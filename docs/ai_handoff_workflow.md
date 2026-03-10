# AI Local Handoff Workflow

This workflow keeps implementation, review, and break-test separated with explicit JSON handoffs.
If you only want two tools, use: Codex for implementation + OpenClaw for review.

## 1) Prepare once

```bash
cd /Users/wuchenghan/Projects/web3-ai-daily-brief
mkdir -p .ai/handoffs
chmod +x scripts/ai/*.sh
```

## 1.5) One-command task setup (recommended)

Pick task size:

- `small` -> single AI gate (`impl -> approved`)
- `medium` -> two AI gates (`impl -> review -> approved`)
- `large` -> three AI gates (`impl -> review -> break_test -> approved`)

```bash
./scripts/ai/start.sh T124 medium main
```

This writes task config into `.ai/tasks/T124.json` and (by default) creates the impl worktree.

## 1.6) Simplest status commands

Use one script for almost everything:

```bash
./scripts/ai/flow.sh T124 impl "impl done"
./scripts/ai/flow.sh T124 review_pass "review passed"
./scripts/ai/flow.sh T124 break_pass "break tests passed"
./scripts/ai/flow.sh T124 status
```

Need role prompt text quickly:

```bash
./scripts/ai/prompt.sh T124 impl
./scripts/ai/prompt.sh T124 review
./scripts/ai/prompt.sh T124 break_test
```

## 1.7) Two-tool mode (Codex + OpenClaw)

Recommended:

```bash
./scripts/ai/start.sh T200 medium main
```

Codex implements and marks done:

```bash
./scripts/ai/flow.sh T200 impl "impl done"
```

OpenClaw reviews and writes verdict automatically:

```bash
OPENCLAW_AGENT=main ./scripts/ai/openclaw_review.sh T200
```

Note: if no diff context is detected, review is auto-marked as fail (`impl_fix`).

Check final state:

```bash
./scripts/ai/flow.sh T200 status
```

Or let the helper decide the next action:

```bash
./scripts/ai/next.sh T200
./scripts/ai/next.sh T200 --run   # auto-run OpenClaw when NEXT=review
```

## 2) Create isolated worktree for a task

```bash
./scripts/ai/create_task_worktrees.sh T123 main
```

This creates:

- implementation worktree and branch: `codex/T123-impl`
- (later) review and break-test detached worktrees at the same commit

## 3) Start watcher (optional)

In a separate terminal:

```bash
./scripts/ai/watch.sh
```

When `impl.json` is written with `impl_done`, it sends a local notification.

## 4) Handoff state machine

State order:

`impl_done -> review_pass/review_fail -> break_pass/break_fail -> approved`

Any `*_fail` sends the task back to implementation (`NEXT=impl_fix`).

### Implementation complete

```bash
./scripts/ai/handoff.sh T123 impl impl_done review "Implemented CSV export"
./scripts/ai/gate.sh T123
```

Expected output:

```text
NEXT=review
```

### Reviewer complete

Pass:

```bash
./scripts/ai/handoff.sh T123 review review_pass break_test "No P1/P2 issues"
```

Fail:

```bash
./scripts/ai/handoff.sh T123 review review_fail impl_fix "Found permission bug"
```

### Break-test complete

Pass:

```bash
./scripts/ai/handoff.sh T123 break_test break_pass approved "All adversarial tests pass"
```

Fail:

```bash
./scripts/ai/handoff.sh T123 break_test break_fail impl_fix "OOM on 100k rows"
```

### Final gate check

```bash
./scripts/ai/gate.sh T123
```

Only when output is `NEXT=approved` should you move to the next project step.
