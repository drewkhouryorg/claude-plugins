# Replay

Scores the nudge's rules against your own past sessions, so you can choose thresholds that fit how you work.

```sh
python3 replay.py
```

It reads Claude Code's transcripts in `~/.claude/projects/` and only reads them: nothing is written or sent anywhere. Sessions with fewer than 10 prompts are skipped.

For each turn end, it notes what happened: commits, pushes, PRs, deploys, tests and how full the context was. It also notes whether you took a break soon after: a `/compact`, a `/clear`, or a prompt that winds down, such as "are we done?" or "hand over". Then it prints, for each candidate rule:

- **fires:** how many turn ends it would have fired on.
- **prec next / prec ≤3:** how often a break followed within one prompt, or within three.
- **recall ≤3:** how many of your breaks it would have caught early.
- **lift:** how much likelier a break was after it fired than after an average turn end.

A good rule has high lift without firing all the time. The plugin's strong note uses the rule "(ship or done) + ctx >= 60%". It also gives a softer note from 45%, which this replay doesn't score yet. If yours lands better at another level, change `STRONG_PCT` or `SOFT_PCT` in `../hooks/decide.ts`.

The patterns that count as winding down are `WIND_DOWN` in `turns.py`. Add the phrases you use.
