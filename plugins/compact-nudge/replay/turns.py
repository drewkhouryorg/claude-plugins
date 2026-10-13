"""Parse Claude Code transcripts into human turns. Read-only."""
import glob
import json
import os
import re

ROOT = os.path.expanduser("~/.claude/projects")

WIND_DOWN = re.compile(
    r"/compact|/clear|\bcompact\b|\bcompress|hand ?over|hand ?off|"
    r"are (we|you) done|we'?re done|done here|close (you|this|the session|down)|"
    r"new (fresh )?sess?ion|open threads?|outstanding|anything (left|missing)|"
    r"lose ends|loose ends|context is (at |huge|large|too big)|"
    r"\b(at|is) \d\d ?%|\d\d ?% context",
    re.I,
)
TEST_CMD = re.compile(r"\b(pytest|jest|vitest|playwright|go test|cargo test|npm (run )?test|make (test|check|smoke|ci)|bun test)\b")
COMMIT_OK = re.compile(r"\[[^\]\n]+ [0-9a-f]{7,}\]|\b[0-9a-f]{7}\b \w+(\(|:)|files? changed")
DEPLOY_CMD = re.compile(r"make\b(\s+-C\s+\S+)?(\s+\S+=\S+)*\s+deploy|firebase deploy|gh workflow run\S* .*deploy")


def human_text(d):
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return None
    o = d.get("origin") or {}
    if o.get("kind") and o["kind"] != "human":
        return None
    c = d["message"].get("content")
    if isinstance(c, list):
        if any(b.get("type") == "tool_result" for b in c):
            return None
        c = " ".join(b.get("text", "") for b in c if b.get("type") == "text")
    if not isinstance(c, str) or not c.strip():
        return None
    if c.startswith(("<task-notification", "<local-command", "<system-reminder", "<bash-stdout", "<bash-stderr")):
        return None
    if "<teammate-message" in c[:200] or c.startswith("[Request interrupted"):
        return None
    return c


def result_text(b):
    c = b.get("content")
    if isinstance(c, list):
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ""


def new_turn(prompt, ts):
    return dict(prompt=prompt, start=ts, end=ts, ctx=0, commit=False, push=False,
                pr=False, merge=False, deploy=False, test_ok=False, test_fail=False,
                tools=0, files=set(), compact_after=None, last_text="")


def parse(path):
    turns, pending = [], {}
    cur = None
    for line in open(path):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        if d.get("subtype") == "compact_boundary":
            if cur:
                cur["compact_after"] = d["compactMetadata"]["trigger"]
            continue
        ts = d.get("timestamp")
        h = human_text(d)
        if h is not None:
            if "<command-name>/compact" in h or h.lstrip().startswith("/compact"):
                continue  # the compact itself is not a turn
            cur = new_turn(h, ts)
            turns.append(cur)
            continue
        if cur is None:
            continue
        if ts:
            cur["end"] = ts
        if d.get("type") == "assistant":
            u = d["message"].get("usage") or {}
            tot = u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            if tot:
                cur["ctx"] = tot
            for b in d["message"].get("content") or []:
                if b.get("type") == "text" and b.get("text", "").strip():
                    cur["last_text"] = b["text"]
                if b.get("type") != "tool_use":
                    continue
                cur["tools"] += 1
                inp = b.get("input") or {}
                if isinstance(inp, dict):
                    fp = inp.get("file_path")
                    if fp:
                        cur["files"].add(fp)
                    if b["name"] == "Bash":
                        pending[b["id"]] = inp.get("command", "")
        elif d.get("type") == "user":
            c = d["message"].get("content")
            if not isinstance(c, list):
                continue
            for b in c:
                if b.get("type") != "tool_result" or b.get("tool_use_id") not in pending:
                    continue
                cmd = pending.pop(b["tool_use_id"])
                err = bool(b.get("is_error"))
                out = result_text(b)
                if re.search(r"git\b.*\bcommit\b", cmd) and not err and COMMIT_OK.search(out):
                    cur["commit"] = True
                if re.search(r"\bgit push\b", cmd) and not err:
                    cur["push"] = True
                if re.search(r"gh pr create", cmd) and not err:
                    cur["pr"] = True
                if re.search(r"gh pr merge|git merge", cmd) and not err:
                    cur["merge"] = True
                if DEPLOY_CMD.search(cmd) and not err:
                    cur["deploy"] = True
                if TEST_CMD.search(cmd):
                    cur["test_ok" if not err else "test_fail"] = True
    return turns


def sessions(min_turns=10):
    for f in sorted(glob.glob(os.path.join(ROOT, "*", "*.jsonl"))):
        t = parse(f)
        if len(t) >= min_turns:
            yield f, t
