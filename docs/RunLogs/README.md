# Run Logs

Model reasoning logs — what was attempted in each development session, why each decision was made, what failed, and what was learned.

## Structure

Each subfolder is a date (`YYYY-MM-DD`). Each file within is a session log.

```
RunLogs/
├── README.md
├── 2026-06-13/
│   └── design-session.md   ← initial design, HLD → LLD → Agent.md
└── <next-date>/
    └── <session-name>.md
```

## Log Template

When you start a development session, create a log file:

```markdown
# Run Log — YYYY-MM-DD — [session title]

## Goal
What were you trying to accomplish this session?

## Starting State
What was already built? What was broken?

## Decision Log

### Decision 1: [short title]
**Options considered:**
- Option A: ...
- Option B: ...

**Chosen:** Option A  
**Why:** ...  
**Trade-off accepted:** ...

### Decision 2: ...

## What Worked
- ...

## What Failed
- Attempt: ...
- Why it failed: ...
- What was tried next: ...

## What's Left
- ...

## Lessons Learned
- ...
```

## Why This Matters

When you return to this project after a break — or when another developer joins — they can read run logs to understand *why* the code looks the way it does. Architecture decisions that seem obvious in the moment are opaque six months later.

**Rule:** If you make a non-obvious decision during development (chose library X over Y, structured code Z way, skipped feature W), write it in the run log for that session.
