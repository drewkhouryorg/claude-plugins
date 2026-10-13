# compact-nudge

A Claude Code plugin that tells you when it's a good moment to `/compact`. When a turn ends at a clean stopping point and your context is filling up, a one-line note appears above the prompt:

```
▸ Clean point: work just shipped, context 52%. Fine to keep going, cheap to /compact now.
▸ Good time to break: Claude says it is done, context 64%. /compact or hand over before the next task.
```

The note goes away when you send your next prompt. It works on its own, and alongside any status line, including [claude-statusline](https://github.com/drewkhouryorg/claude-statusline).

## Display only

Nothing this plugin does reaches the model. It never adds to the prompt, the context or the transcript, so it can't make Claude stop, change course or ask you anything. It only draws in the band above the prompt and, for the stronger note, shows a toast.

That's checked three ways:

- `claude plugin validate` lists every hook and call the plugin makes, and `tests/test_nudge.py` in the repo fails if anything outside a fixed set appears. The set is drawing, reading usage and its own state, and listening for prompts, Bash calls and turn ends.
- `hooks/register.test.tsx` runs a full sequence: a commit, a turn end that fires the note, the note drawn, the next prompt. It then checks that the prompt, the context and the transcript are untouched.
- The same test file has been run against deliberately broken copies of the plugin (adding context, appending to the transcript, adding text under the answer). Each broken copy fails it.

## When it fires

A turn has to end with both of these true:

1. **Something finished.** Either the turn ran a successful ship command, or Claude's reply says the work is done.
   - **Ship commands:** `git commit`, `git push`, `git merge`, `gh pr create`, `gh pr merge`, `make ... deploy`, `firebase deploy`. A `--dry-run` doesn't count, and nor do `git merge-base` or `git stash push`.
   - **"Done" phrases**, in the last 600 characters of the reply: "merged", "deployed", "shipped", "all green", "is live", "nothing left", "nothing outstanding", "nothing open", "all done", "done.", "landed", "wrapped up". "done." is the broadest: any reply ending a sentence with "done" counts.
2. **Context is at 45% or more.** From 45% it's the soft note. From 60% it's the strong one, in yellow with a toast.

After a note, it stays quiet until context grows another 10%, except that crossing 60% always fires. A `/compact` or `/clear` starts that over. Subagents' turns and interrupted turns never fire it.

The thresholds come from replaying 48 real sessions. A clean point at 60% or more was followed by a break within three prompts 32% of the time, against 11% for an average turn end. Your habits may differ: [`replay/`](replay) scores the same rules against your own sessions.

## Install

It needs Claude Code 2.1.287 or later, where plugins with code (mods) are on by default. Claude Code from 2.1.275 to 2.1.286 accepts the install command below, but the plugin then does nothing. Run `claude --version` first.

From the marketplace this repo provides:

```
/plugin install compact-nudge --marketplace drewkhouryorg/claude-plugins
```

In a session, this opens the plugin panel on its details rather than installing straight away. Choose a scope there: "user" for every project.

Or from a local copy, by adding it to the `env` block of `~/.claude/settings.json`. The path must be absolute or start with `~`, and this needs Claude Code 2.1.280 or later. If you already have an `env` block, add the line to it:

```json
{
  "env": {
    "CLAUDE_CODE_PLUGIN_DIRS": "~/code/claude-plugins/plugins/compact-nudge"
  }
}
```

## Updates

Claude Code doesn't update plugins from marketplaces like this one by itself. To get a new version, run `/plugin marketplace update drewkhouryorg`.

## What it runs

A mod is code, and it runs with your permissions in every session that loads the plugin, including `claude -p` and the Agent SDK, where it has nothing to draw. This one only does what [Display only](#display-only) lists: `claude plugin validate plugins/compact-nudge` prints every hook and call it makes, so you can check. `"disableAllHooks": true` turns it off, along with your status line.

## Change it

The rules are in `hooks/decide.ts`:

- `SOFT_PCT`, `STRONG_PCT` and `COOLDOWN_PCT` set the thresholds.
- `SHIP_CMD` decides which commands count as shipping.
- `DONE_TEXT` decides which phrases count as done.

The wording is in `message()`. Run the tests after a change:

```sh
claude plugin test plugins/compact-nudge
claude plugin validate plugins/compact-nudge
```
