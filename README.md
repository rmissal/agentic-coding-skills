# agentic-coding-skills

A standalone, brand-neutral library of [Claude Code](https://docs.claude.com/en/docs/claude-code) /
[agentskills.io](https://agentskills.io) **skills** that encode general
software-engineering practice — clean coding, requirements engineering, PR
finalization, test quality, output evaluation, git hygiene — plus the meta-skills
that create, grade, and guard the library itself.

Nothing here is tied to a specific language, framework, repository, model, or
coding agent. The skills live in a neutral top-level `skills/` directory — no
coding agent is privileged. Clone it, run setup, and the skills become available
to every project and coding agent on your machine.

- **Multi-language** — the `coding` skill covers Python, TypeScript, YAML,
  Gherkin, and shell, and its core discipline is *discover the repo's own
  toolchain first*, which is language-agnostic.
- **Multi-project** — zero hardcoded repositories; skills operate on whatever
  repo they run in. A machine-local `projects-db.md` roster indexes multiple
  repos; per-repo context is read from each repo's own README/ARCHITECTURE/CLAUDE.
- **Multi-model / multi-agent** — model-agnostic prose, agentskills.io
  frontmatter, and a `~/.agents/skills/` junction so agents beyond Claude Code
  (Cursor, Cline, …) can discover the skills.
- **Self-onboarding & self-improving** — setup bootstraps its own wiring and
  project roster; `skill-creator` + `grade-skills` + `skill-quality` form a
  closed maintenance loop that sharpens skills without letting them drift out of
  their declared functional domain.

Licensed under **Apache-2.0** (see [LICENSE](LICENSE)).

## Install

```bash
git clone <this-repo> agentic-coding-skills
cd agentic-coding-skills
bash scripts/setup.sh          # Windows: scripts\setup.bat  or  scripts\setup.ps1
```

Setup is idempotent and does the following:

1. Generates the harness discovery paths from the committed `skills/` source:
   per-skill links into `.claude/skills/` (Claude Code) and `.agents/skills/`
   (agentskills.io / cross-tool), plus their user-scope equivalents
   (`~/.claude/skills/`, `~/.agents/skills/`), so every project and coding agent
   sees the skills with `skills/` as the single live source of truth.
2. Installs the upstream `skill-creator` and `mcp-builder` skills from
   [anthropics/skills](https://github.com/anthropics/skills) (MIT, gitignored,
   not vendored) into the generated harness paths. Warns instead of failing if
   offline.
3. Wires the git pre-commit hook (`git config core.hooksPath scripts/git-hooks`).
4. Creates `projects-db.md` from `projects-db.md.example` if absent (gitignored).

No secret fetching, no MCP-server build, no external services required.

## Skill catalog

| Skill | Domain | Invoke |
|---|---|---|
| `coding` | Writing, editing, reviewing code across languages | auto |
| `requirements-engineering` | Turning a vague ask into a verifiable spec before building | auto |
| `finalize-and-open-pr` | Pre-push self-review + formatter + PR creation | `/finalize-and-open-pr` |
| `test-quality` | Validate-before-assert; SMOKE/STANDARD/FULL test rigor | auto |
| `agent-output-eval` | Harness for grading agent/skill output quality | auto |
| `git-cleanup` | Prune stale local branches across your repos | `/git-cleanup` |
| `projects-db` | Maintain the machine-local multi-repo roster | `/projects-db` |
| `grade-skills` | Grade + auto-optimize skill trigger descriptions | `/grade-skills` |
| `skill-quality` | Portability + functional-domain guardian for the library | `/skill-quality` |
| `project-management` | Govern project lifecycle, milestone roadmaps, sprints, and artifact sync | `/project-management` |
| `safe-ftp-deploy` | Pre-upload security audit & safe deployment to FTP/FTPS/SFTP | auto |
| `skill-creator` | *(upstream, installed at setup)* author/optimize skills | `/skill-creator` |
| `mcp-builder` | *(upstream, installed at setup)* build MCP servers | `/mcp-builder` |

## Using with other coding agents

The `~/.agents/skills/` link and per-repo `.agents/skills` junction follow the
agentskills.io convention, so tools that read that path (Cursor, Cline, and
others) discover the same skills. The prose is model-agnostic — no hardcoded model
IDs or tool names in skill logic — so it reads correctly regardless of which model
backs your agent.

## Maintaining the library

Three orthogonal quality mechanisms keep the library healthy:

1. **`validate_skill_frontmatter.py`** — strict-YAML validity (folded-scalar rule).
   Runs in the pre-commit hook and CI.
2. **`grade-skills`** — trigger-correctness: does each skill fire on the right
   prompts and stay quiet otherwise. Run `/grade-skills` to grade and optionally
   auto-optimize descriptions.
3. **`skill-quality`** — portability + functional-domain integrity: no leaked
   paths/brands/model-IDs, every skill declares `metadata.domain`, no skill
   invents a per-repo context file. Runs `/skill-quality` and in CI
   (`scripts/skill_audit.py`).

To add a skill: use `/skill-creator`, declare its `metadata.domain`, add
`evals/queries.json`, then run `/grade-skills` and `/skill-quality`. See
[CLAUDE.md](CLAUDE.md) for the frontmatter rules.
