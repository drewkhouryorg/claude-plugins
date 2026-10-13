![claude-plugins logo](images/logo.svg)

# claude-plugins

Claude Code plugins by Drew Khoury, published as a plugin marketplace.

| Plugin | What it does |
| - | - |
| [compact-nudge](plugins/compact-nudge) | Tells you when it's a good moment to `/compact`: when a turn ends at a clean stopping point and your context is filling up, a note appears above the prompt. Display only: the model never sees it. |

## Install

Plugins with code (mods) need Claude Code 2.1.287 or later. Check with `claude --version`.

In Claude Code, add the marketplace once, then install what you want from it:

```
/plugin marketplace add drewkhouryorg/claude-plugins
/plugin install compact-nudge@drewkhouryorg
```

Or install one plugin without adding the marketplace first:

```
/plugin install compact-nudge --marketplace drewkhouryorg/claude-plugins
```

In a session, an install opens the plugin panel on its details, where you choose a scope: "user" for every project.

## Updates

Claude Code doesn't update plugins from this marketplace by itself. To get new versions, run `/plugin marketplace update drewkhouryorg`.

## Before you install

A plugin with code runs with your permissions, in every session that loads it. Each plugin's README says what it does, and `claude plugin validate plugins/<name>` lists every hook and call a plugin makes, so you can check before you install. `"disableAllHooks": true` in your settings turns them all off.

## Tests

```sh
make test
```

That runs this repo's own checks, then each plugin's tests and Claude Code's validator on it. The plugin parts need the `claude` CLI, and skip without it.

## License

MIT. See [LICENSE](LICENSE).
