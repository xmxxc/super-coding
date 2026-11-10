# super-coding

A multi-ticket development workflow for coding agents: one controller dispatches implementation and independent review to Codex, OpenCode or Claude Code sessions, sleeps while they work, and is woken by their messages. Fix rounds go back to the original implementer and incremental reviews to the original reviewer; a final full review comes before release, and live acceptance is handed to `live-verify`.

This repository holds the skills. The dispatcher they drive, `wfc`, is a separate download from [xmxxc/workflow-core](https://github.com/xmxxc/workflow-core).

## Install

Requirements: Linux or macOS (on Windows, use WSL2), python3 (3.9+), tmux, `wfc` on PATH, `gh` for GitHub tickets, and the host CLIs you dispatch to.

1. Download `super-coding-<version>.tar.gz` from Releases and unpack it (or clone this repository).
2. Run `python3 install.py`. It installs `super-coding` into `~/.claude/skills` and `~/.codex/skills`, and the `ai-coding` and `live-verify` prototypes only where you have none of your own. A linked development install is left alone.
3. `ai-coding` uses further general skills (`code-review`, `implement`, `tdd` and so on) from the user's skills collection; install those separately.

Then start a controller session and invoke `super-coding` with the repository and the tickets in scope.

## Layout

- `skills/super-coding/`: the controller skill. `references/router.md` covers dispatch, waiting, continue/resume, message handling and recovery.
- `skills/super-coding/scripts/ctl.py`: the controller's routine checks between rounds (snapshot checks with real exit codes, candidate read-back, transcribing an offline reviewer's record, lifecycle label switch). Python standard library; uses git and gh. The skill runs it from its own directory, so installing the skill installs the script.
- `skills/ai-coding/`: a pinned copy of the prototype. `skills/live-verify/`: forked from the skills repository and maintained here. See [skills/VENDORED.md](skills/VENDORED.md).
- `install.py`: the installer. `tests/`: `test_ctl.py` (real git, fake gh) and `test_install.py` (throwaway HOME).

## Development

Run the tests with `python3 -m unittest discover -s tests`. CI runs them on Ubuntu and macOS with Python 3.9 and 3.12. To release, push a tag `v<version>`; the release workflow tests, packs `skills/`, `install.py`, `README.md` into `super-coding-<version>.tar.gz` with its SHA-256 and publishes them.

The design record (decisions, host probes, review history) lives with the dispatcher in xmxxc/workflow-core.
