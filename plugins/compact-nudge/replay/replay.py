"""Replay transcripts and score break-point heuristics against what the user actually did."""
import re
import statistics as st
from collections import defaultdict

from turns import WIND_DOWN, sessions

DONE_TEXT = re.compile(r"\b(merged|deployed|shipped|all green|is live|nothing (left|outstanding|open)|all done|done\.|landed|wrapped up)\b", re.I)
CLOSURE = re.compile(r"\b(approved?|merge it|ship it|thanks|thank you|perfect|lgtm|looks good|nice|great)\b", re.I)


def label(turns):
    """For each turn end, is it where a break started? None = already winding down, skip."""
    wind = [bool(WIND_DOWN.search(t["prompt"][:400])) for t in turns]
    out = []
    for i, t in enumerate(turns):
        if wind[i]:
            out.append(None)
            continue
        nxt = i + 1 < len(turns)
        out.append(dict(
            now=(nxt and wind[i + 1]) or t["compact_after"] == "manual",
            # broke within the next 3 prompts (one more small ask, then wind-down)
            soon=any(wind[j] for j in range(i + 1, min(i + 4, len(turns)))) or t["compact_after"] == "manual",
            end=not nxt,
        ))
    return out


def signals(turns, i, window):
    t = turns[i]
    recent_fail = any(turns[j]["test_fail"] for j in range(max(0, i - 5), i + 1))
    ship = t["commit"] or t["push"] or t["pr"] or t["merge"] or t["deploy"]
    pct = t["ctx"] / window
    done = bool(DONE_TEXT.search(t["last_text"][-600:]))
    return {
        "claude says done": done,
        "claude says done + ctx >= 50%": done and pct >= 0.5,
        "claude says done + ctx >= 70%": done and pct >= 0.7,
        "(ship or done) + ctx >= 60%": (ship or done) and pct >= 0.6,
        "ship (commit/push/pr/merge/deploy)": ship,
        "commit": t["commit"],
        "push/pr/merge": t["push"] or t["pr"] or t["merge"],
        "deploy": t["deploy"],
        "tests green after red": t["test_ok"] and recent_fail,
        "closure words in prompt": bool(CLOSURE.search(t["prompt"][:300])),
        "ctx >= 50%": pct >= 0.5,
        "ctx >= 70%": pct >= 0.7,
        "ship + ctx >= 40%": ship and pct >= 0.4,
        "ship + ctx >= 50%": ship and pct >= 0.5,
        "(ship or closure) + ctx >= 50%": (ship or bool(CLOSURE.search(t["prompt"][:300]))) and pct >= 0.5,
    }


def main():
    stats = defaultdict(lambda: dict(fire=0, now=0, soon=0))
    base = dict(n=0, now=0, soon=0)
    leads, autos = [], []
    nsess = 0
    for f, turns in sessions():
        nsess += 1
        window = 1_000_000 if max(t["ctx"] for t in turns) > 210_000 else 200_000
        labels = label(turns)
        last_ship = None  # (turn index, ctx%) since the previous break
        for i, lab in enumerate(labels):
            t = turns[i]
            if t["compact_after"] == "auto":
                autos.append(last_ship)
                last_ship = None
            if lab is None:
                last_ship = None
                continue
            sig = signals(turns, i, window)
            base["n"] += 1
            base["now"] += lab["now"]
            base["soon"] += lab["soon"]
            for k, v in sig.items():
                if v:
                    s = stats[k]
                    s["fire"] += 1
                    s["now"] += lab["now"]
                    s["soon"] += lab["soon"]
            if lab["now"] and last_ship is not None:
                leads.append((i - last_ship[0], t["ctx"] / window - last_ship[1]))
            if lab["now"]:
                last_ship = None
            elif sig["ship + ctx >= 40%"]:
                last_ship = (i, t["ctx"] / window)
    print(f"sessions={nsess} candidate turn-ends={base['n']} breaks-next={base['now']} breaks-within-3={base['soon']}")
    if not base["soon"]:  # every rate below is out of the breaks
        print("No breaks to score against yet: no session with 10 or more prompts had a /compact,"
              " a /clear or a wind-down prompt.")
        return
    print(f"base rate: next={base['now']/base['n']:.1%}  within-3={base['soon']/base['n']:.1%}\n")
    print(f"{'signal':38} {'fires':>6} {'prec next':>10} {'prec ≤3':>8} {'recall ≤3':>10} {'lift':>5}")
    for k, s in stats.items():
        pn, ps = s["now"] / s["fire"], s["soon"] / s["fire"]
        print(f"{k:38} {s['fire']:6} {pn:10.1%} {ps:8.1%} {s['soon']/base['soon']:10.1%} {ps/(base['soon']/base['n']):5.1f}")
    print(f"\nbreaks with an earlier clean point (ship + ctx>=40%) in the same stretch: {len(leads)} of {base['now']}")
    if leads:
        print(f"  median turns earlier: {st.median(x for x, _ in leads)}  median ctx earlier: {st.median(y for _, y in leads):.0%}")
    print(f"auto-compacts: {len(autos)}, with an earlier clean point: {sum(a is not None for a in autos)}")


if __name__ == "__main__":
    main()
