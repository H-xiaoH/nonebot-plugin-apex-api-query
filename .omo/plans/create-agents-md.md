# Create AGENTS.md

## TL;DR

> **Quick Summary**: Create a compact `AGENTS.md` instruction file for the repository capturing hard-earned context that future OpenCode sessions would otherwise miss.
>
> **Deliverables**:
> - `AGENTS.md` at repository root
>
> **Estimated Effort**: Quick
> **Parallel Execution**: NO - single task

---

## Context

### Original Request
Create `AGENTS.md` for this repository — a compact instruction file to help future OpenCode sessions avoid mistakes and ramp up quickly.

### Research Summary
- Single-package NoneBot2 plugin (8 source files, flat structure)
- Two separate API endpoints (mozambiquehe.re + apexlegendsstatus.com)
- Mandatory `APEX_API_KEY` with runtime validation blocking plugin load
- PIL-based image rendering with Chinese font dependency
- SQLAlchemy ORM via nonebot_plugin_orm, auto-creates table on startup
- No test infrastructure, no lint/typecheck config
- Poetry build system, CI publishes to PyPI on push to main
- No existing AGENTS.md, CLAUDE.md, or opencode.json

---

## Work Objectives

### Core Objective
Write a compact `AGENTS.md` at repo root with high-signal, repo-specific guidance.

### Concrete Deliverables
- `AGENTS.md` at repository root

### Must Have
- Two API endpoint distinction (mozambiquehe.re vs apexlegendsstatus.com)
- Mandatory config note (APEX_API_KEY blocks load)
- Image fallback pattern documentation
- Font dependency and location
- No test infrastructure warning
- Architecture overview (flat single-package)

### Must NOT Have
- Generic Python/NoneBot advice
- Long tutorials
- Speculative or unverified claims

---

## TODOs

- [x] 1. Write AGENTS.md

  **What to do**:
  - Create `/Users/hxiaoh/Documents/GitHub/nonebot-plugin-apex-api-query/AGENTS.md`
  - Write compact, bullet-oriented content covering: quickstart commands, architecture overview, two-API-endpoint distinction, mandatory config note, command flow, database auto-creation, image rendering quirks (font path, map cache, fallback), translations location, CI/release pattern, no-test-infrastructure warning.
  - Re-read and trim anything generic or obvious.

  **Must NOT do**:
  - Do not include generic Python or NoneBot2 advice
  - Do not include speculative or unverified claims
  - Do not include long tutorials or exhaustive file trees

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single markdown file write, well-researched, no complex decisions
  - **Skills**: []
  - **Skills Evaluated but Omitted**: All — task is a write-only operation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sole task
  - **Blocks**: Nothing
  - **Blocked By**: None

  **References**:
  - `README.md:84-98` — Config table for exact env var names and defaults
  - `config.py:5-31` — Pydantic model with mandatory key validator
  - `data_source.py:27-70` — Two API endpoints and `_fetch` pattern
  - `__init__.py:60-134` — Handler fallback pattern (render → text on error)
  - `image.py:87-89` — Font path (`Path(__file__).parent / "fonts" / "NotoSansSC...`)
  - `models.py:10-24` — SQLAlchemy model with auto-create on startup
  - `pyproject.toml:28-29` — Entry point declaration
  - `.github/workflows/publish.yml` — CI publish to PyPI

  **Acceptance Criteria**:
  - [ ] File exists: `/Users/hxiaoh/Documents/GitHub/nonebot-plugin-apex-api-query/AGENTS.md`
  - [ ] File is under 100 lines (compact)
  - [ ] Contains: two-API-endpoint note, mandatory config, font path, no-tests warning
  - [ ] Does NOT contain: generic Python advice, unverified claims

  **QA Scenarios**:

  ```
  Scenario: File exists with expected content
    Tool: Bash
    Preconditions: None (greenfield file)
    Steps:
      1. ls -la AGENTS.md — verify file exists and is non-empty
      2. wc -l AGENTS.md — verify under 100 lines
      3. grep "mozambiquehe.re" AGENTS.md — verify two-endpoint distinction documented
      4. grep "apexlegendsstatus.com" AGENTS.md — verify second endpoint documented
      5. grep "MissingAPIKeyError" AGENTS.md — verify mandatory config noted
      6. grep "NotoSansSC" AGENTS.md — verify font documented
      7. grep "test" AGENTS.md — verify no-test-infra warning present
      8. grep -i "generic\|simple\|obvious" AGENTS.md — verify no fluff (should return nothing incriminating)
    Expected Result: File exists, 50-100 lines, all key facts present
    Evidence: .omo/evidence/task-1-agents-md-check.txt
  ```

  **Commit**: YES
  - Message: `docs: add AGENTS.md with repo onboarding guide`
  - Files: `AGENTS.md`

---

## Success Criteria

### Verification Commands
```bash
ls -la AGENTS.md           # Expected: file exists, >0 bytes
wc -l AGENTS.md            # Expected: 50-100 lines
grep -c "mozambiquehe" AGENTS.md  # Expected: 1
grep -c "apexlegendsstatus" AGENTS.md  # Expected: 1
grep -c "NotoSansSC" AGENTS.md    # Expected: 1
grep -c "test" AGENTS.md          # Expected: >=1 (no-test-infra note)
```

### Final Checklist
- [ ] File exists at repo root
- [ ] Two API endpoints documented
- [ ] Mandatory config documented
- [ ] Font dependency documented
- [ ] No generic/obvious advice included
