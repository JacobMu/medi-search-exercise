# Agent Orchestration — image-compositor

This workspace uses an Atlas-style conductor-delegate multi-agent system covering the full development lifecycle: **Plan → Implement → Review → Commit**.

## Plan Directory

```
plans/
```

---

## Agent Roster

### Orchestrators

| Agent | Role | When to invoke |
|-------|------|----------------|
| **Atlas** | CONDUCTOR — orchestrates full lifecycle | `@Atlas implement the plan in plans/…` |
| **Prometheus** | PLANNER — researches codebase, writes TDD plans | `@Prometheus plan <feature>` |

### Subagents (called by orchestrators, usable standalone)

| Agent | Role | Equivalent in Atlas repo |
|-------|------|--------------------------|
| **Oracle-subagent** | RESEARCHER — deep context gathering, structured findings | Oracle-subagent |
| **Explore** | SCOUT — fast read-only file & usage discovery | Explorer-subagent |
| **SWE** | IMPLEMENTER — feature dev, TDD, linting | Sisyphus-subagent |
| **SE: Security** | REVIEWER — OWASP/LLM security + code quality review | Code-Review-subagent |

---

## Typical Workflow

```
User → @Prometheus plan <feature>
           ├─ @Explore (find relevant files)
           ├─ @Oracle-subagent (deep subsystem research)
           └─ Writes plans/<feature>-plan.md → offers handoff ↓

       → @Atlas implement the plan in plans/<feature>-plan.md
           ├─ Phase N: @SWE (write tests → fail → code → pass → lint)
           ├─ Review:  @SE: Security (APPROVED / NEEDS_REVISION / FAILED)
           └─ Pause → user commits → next phase
```

---

## Skills Available

Load these in agent instructions when relevant:

| Skill | Path | Use when… |
|-------|------|-----------|
| `python-patterns` | `.github/skills/python-patterns/SKILL.md` | Writing Python code (protocols, dataclasses, async, type hints) |
| `pragmatic-programmer` | `.github/skills/pragmatic-programmer/SKILL.md` | Architecture decisions, DRY, tracer bullets |

---

## Project Context

- **Stack:** Python / FastAPI backend (`be/`)
- **Purpose:** Ad creative compositor — replaces green-screen phone displays with app screenshots
- **Routers:** `overlay`, `save`, `stats`
- **Services:** `compositor`, `analytics`
- **Tests:** add to the `be/` tree; run with `pytest`
- **Code style:** follow existing patterns; linting via `pyproject.toml`
