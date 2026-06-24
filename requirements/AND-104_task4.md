# AND-104 Task 4: Development Workflow Hooks

**Action:** Implement hooks to automate and enforce your development workflow

**Tools:** Claude Code

**Spec Files Modified:** N/A

---

## Detailed Requirements

Now that you have written Go code and experienced the development workflow, it is time to implement the hooks you identified in your Task 1 audit. If your understanding of which rules need deterministic enforcement has changed since Task 1 (it probably has), update your audit categorizations and justifications before proceeding.

Review your Task 1 audit and implement hooks in .claude/settings.json for three workflow problems:

- **Formatting consistency (PostToolUse):** Auto-format code files when they are modified
- **File protection (PreToolUse):** Choose a file protection target from your audit and justify why it needs deterministic protection rather than an advisory CLAUDE.md rule
- **Task completion awareness (Stop):** Notify you when Claude Code finishes a task

Demonstrate that each hook works correctly. Document your test approach and results in docs/claude_md_audit.md (update the audit document with a new section for hook implementations).

Choose one additional hook based on real friction you experienced while building the Go handlers in Task 3. Implement it, test it, and document in your audit document what problem it solves and why a hook is the right mechanism (rather than a CLAUDE.md rule or a skill).

Commit the hooks configuration and updated audit document.

---

## Deliverable

- .claude/settings.json with hooks configured
- Updated docs/claude_md_audit.md with hook implementation documentation

---

## Evaluation Criteria

- Work starts with a markdown header identifying the task
- PostToolUse hook auto-formats code files after edits
- PreToolUse hook blocks writes to the chosen file(s) with a justification for why that target needs deterministic protection
- Stop hook triggers a notification when Claude finishes
- One additional custom hook is implemented with documentation of the problem it solves
- Each hook is tested with documented results in the audit document
- The audit document explains why each protected file needs a hook rather than a CLAUDE.md rule
