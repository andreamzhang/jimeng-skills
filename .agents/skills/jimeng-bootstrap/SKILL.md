---
name: jimeng-bootstrap
description: Bootstrap a Codex project with the 即梦分镜师 plugin. Use when a user asks to initialize the plugin workflow, install the producer rules, or prepare a short-drama plan in an existing workspace.
---

# 即梦分镜师 · Bootstrap

Use this skill to make the current workspace behave like a `即梦分镜师` project.

## Your job

Make the plugin useful in the user's current project, without changing unrelated files.

Steps:

1. Determine the current project root:
   - Use the root that contains `AGENTS.md`, `.codex/`, or `scripts/`.
   - If none of these exist, treat the current working directory as a new project root.

2. If `AGENTS.md` is missing, add it from the installed plugin:
   - Read `${SKILL_DIR}/../../AGENTS.md`.
   - Write the same content to `<project-root>/AGENTS.md`.

3. If `.codex/agents/`, `.agents/skills/`, or `tools/` are missing:
   - Do **not** create a fake one.
   - Tell the user to use the plugin repository root, or clone `https://github.com/andreamzhang/jimeng-skills.git` into the project root.

4. If creating a new drama, run:
   `tools\py.cmd tools\new_drama_memory.py "<剧名>" --dirs`

5. Do not add extra rules to this skill. This is only a bootstrap helper.
