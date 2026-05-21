# claude-skills

A collection of [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) skills I use day-to-day. Open-sourced for anyone who wants to fork, learn from, or adapt them.

## What is a skill?

A skill is a folder under `~/.claude/skills/<name>/` containing a `SKILL.md` file with YAML frontmatter (`name`, `description`, optional `argument-hint`) followed by Markdown instructions. Claude Code surfaces the skill via `/<name>` and loads its instructions when invoked. See the [official skills docs](https://docs.claude.com/en/docs/claude-code/skills) for details.

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/Magnus-Gille/claude-skills.git ~/.claude/skills
```

Or if `~/.claude/skills` already exists with other skills, clone elsewhere and symlink the ones you want.

After install, restart Claude Code (or wait for the next session) and the skills will appear in the available-skills list.

## Skills in this repo

| Skill | What it does |
|-------|--------------|
| `/close` | Session closing checklist — git snapshot/commit, docs review, local state file update, optional Munin sync. |
| `/commit` | Standardized git commit workflow: author verification, diff review, security check, conventional message, push. |
| `/debate` | Adversarial debate against a cross-model reviewer (Codex or Antigravity/agy) to stress-test a draft, plan, or design before finalizing. Multi-round critique with self-review and summary. Backend chosen via `--model codex\|agy` (defaults to codex). |
| `/eli5` | Re-explain the previous assistant turn in plain language — no jargon, no unexplained acronyms, short sentences. |
| `/issues` | Check GitHub issues for the current repo: list, filter by label, view details, search. |
| `/review-pr-codex` | Cross-model PR review — invokes Codex headless on the current branch diff, then reads findings and fixes or reports. |
| `/security-review` | Full security review: threat model, OWASP Top 10 + LLM Top 10 scan, finding validation, patch proposals. |
| `/user-test-memory` | Spawn three subagents (Opus, Sonnet, Haiku) in parallel to stress-test the Munin memory MCP and produce a synthesized UX report. |

## Dependencies

Some skills shell out to external CLIs or MCP servers:

- **`debate`** — requires the [OpenAI Codex CLI](https://github.com/openai/codex) (for `--model codex`) and/or the Google Antigravity CLI `agy` (for `--model agy`), installed and authenticated.
- **`review-pr-codex`** — requires the [OpenAI Codex CLI](https://github.com/openai/codex) installed and authenticated.
- **`user-test-memory`** — requires the [Munin memory](https://github.com/Magnus-Gille/munin-memory) MCP server registered with Claude Code.
- **`issues`** — requires the [GitHub CLI](https://cli.github.com/) (`gh`).
- **`security-review`** — works standalone; suggested findings can be cross-checked with Codex CLI if available.

The remaining skills (`close`, `commit`, `eli5`) only need standard `git` and Claude Code itself.

## Personal vs public

A separate private repo holds skills that are tightly coupled to my own infrastructure (mail, calendar, accounting, deployment scripts, the Munin/Hugin/Mimir Pi stack). Those aren't useful without that environment, so they live elsewhere. If something looks like it belongs in the public set but isn't here, it's probably intentional.

## Contributing

This is my personal skill collection — I'm not actively soliciting PRs, but bug reports and "your skill broke when X" issues are welcome. Fork freely.

## License

MIT — see [LICENSE](LICENSE).
