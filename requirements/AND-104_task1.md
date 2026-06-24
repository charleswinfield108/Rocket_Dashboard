# AND-104 Task 1: CLAUDE.md Audit and Platform Conventions Skill

**Action:** Audit your existing CLAUDE.md and create a knowledge skill for platform-specific rules

**Tools:** Claude Code

**Spec Files Modified:** N/A

---

## Detailed Requirements

The learning cards for this module introduce hooks, skills, and the extension spectrum. Read those cards before starting this task.

Open your project's CLAUDE.md. Read every rule you have written over Modules 1-3. For each rule, categorize it into one of three buckets: always relevant (stays in CLAUDE.md), must always execute (belongs in a hook; you will implement these in Task 4), or scoped to specific work (belongs in a skill). The learning cards define these categories.

Document your categorization in docs/claude_md_audit.md: list each rule, its category, and a one-sentence justification for why it belongs there. This is a first pass; you will revisit and refine your categorizations as you gain hands-on experience with hooks in later tasks. The goal is that the audit always reflects your current understanding, not that you get it perfect on the first try.

Identify rules from your audit that are scoped to platform work (Python web development, HTMX, server conventions). Create a knowledge skill at .claude/skills/platform-conventions/SKILL.md that:

- Has a description that triggers auto-loading when you are editing files in platform/
- Contains the platform-specific conventions that were in CLAUDE.md
- Keeps CLAUDE.md focused on rules that apply to all work (intelligence layer, documentation, etc.)
- Is under 500 lines (put reference material in supporting files if needed)

After creating the skill, remove the migrated rules from CLAUDE.md. Your CLAUDE.md should be shorter than it was before this module.

Commit your audit document, skill, and updated CLAUDE.md.

---

## Deliverable

- docs/claude_md_audit.md with categorized rules
- .claude/skills/platform-conventions/SKILL.md
- Updated CLAUDE.md

---

## Evaluation Criteria

- Audit document lists every rule from CLAUDE.md with a category and justification
- Work in the audit document starts with a markdown header identifying the task
- Platform conventions skill has a description that references platform/Python/HTMX work
- Platform conventions skill does not set user-invocable: true (it auto-loads based on relevance)
- Rules categorized as "scoped to platform work" are in the skill, not in CLAUDE.md
- CLAUDE.md is shorter after migration (rules moved to the skill are removed from CLAUDE.md)
- Skill is under 500 lines
