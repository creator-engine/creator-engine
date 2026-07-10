#!/usr/bin/env python3
"""
Convert a Claude Code JSONL session transcript to human-readable Markdown.

Schema (confirmed from file inspection):
  Each line is a JSON object with 'type' field. Key types:
  - 'user': has .message.role='user', .message.content = list of blocks or list of strings
      - string list = system/context injection (skip / fold)
      - dict blocks: type='text' (human message), type='tool_result'
  - 'assistant': has .message.role='assistant', .message.content = list of blocks
      - block types: 'thinking', 'text', 'tool_use'
  - 'system': subtype varies (local_command, stop_hook_summary, turn_duration, etc.) — skip/fold
  - 'queue-operation': operator queued a message — render as user turn
  - 'pr-link': PR created — render as info line
  - 'last-prompt': last prompt content — can be shown as user prompt if it's the opener
  - 'attachment', 'mode', 'file-history-snapshot', 'ai-title' — skip (noise)
"""

import sys
import json
import re
import os
from datetime import datetime, timezone

INPUT = "/home/cedev2/creator-engine/.ce/state/research/TRANSCRIPT_CE_DEV2_20260621_companybrain-worksizing-foreman.jsonl"
OUTPUT = "/home/cedev2/creator-engine/.ce/state/research/TRANSCRIPT_CE_DEV2_20260621_companybrain-worksizing-foreman.readable.md"
TRUNCATE_LIMIT = 600

def fmt_timestamp(ts: str) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts

def truncate(text: str, limit: int = TRUNCATE_LIMIT) -> str:
    if len(text) <= limit:
        return text
    overflow = len(text) - limit
    return text[:limit] + f"\n… [truncated {overflow:,} chars]"

def render_tool_use(block: dict) -> str:
    name = block.get("name", "UnknownTool")
    inp = block.get("input", {})

    # Compact rendering per tool type
    lines = [f"**`{name}`**"]

    if name == "Bash":
        cmd = inp.get("command", "")
        desc = inp.get("description", "")
        if desc:
            lines.append(f"  _description:_ {desc}")
        if cmd:
            cmd_disp = truncate(cmd, 300)
            lines.append(f"  ```bash\n  {cmd_disp}\n  ```")
    elif name in ("Read",):
        fp = inp.get("file_path", "")
        extras = []
        if inp.get("offset"):
            extras.append(f"offset={inp['offset']}")
        if inp.get("limit"):
            extras.append(f"limit={inp['limit']}")
        suffix = f" ({', '.join(extras)})" if extras else ""
        lines.append(f"  `{fp}`{suffix}")
    elif name in ("Edit",):
        fp = inp.get("file_path", "")
        lines.append(f"  `{fp}`")
        old = inp.get("old_string", "")
        new = inp.get("new_string", "")
        if old:
            lines.append(f"  _replace:_ `{truncate(old, 120)}`")
        if new:
            lines.append(f"  _with:_ `{truncate(new, 120)}`")
    elif name in ("Write",):
        fp = inp.get("file_path", "")
        content = inp.get("content", "")
        lines.append(f"  `{fp}` ({len(content):,} chars)")
    elif name == "Agent":
        desc = inp.get("description", "")
        prompt = inp.get("prompt", "")
        subtype = inp.get("subagent_type", "")
        model = inp.get("model", "")
        if desc:
            lines.append(f"  _description:_ {desc}")
        if subtype:
            lines.append(f"  _subagent_type:_ `{subtype}`")
        if model:
            lines.append(f"  _model:_ `{model}`")
        if prompt:
            lines.append(f"  _prompt:_ {truncate(prompt, 300)}")
    elif name == "Skill":
        skill = inp.get("skill", "")
        args = inp.get("args", "")
        lines.append(f"  _skill:_ `{skill}`")
        if args:
            lines.append(f"  _args:_ {args}")
    elif name in ("WebSearch", "WebFetch"):
        q = inp.get("query", inp.get("url", ""))
        lines.append(f"  `{truncate(q, 200)}`")
    elif name == "TaskCreate":
        desc = inp.get("description", "")
        ptype = inp.get("type", "")
        lines.append(f"  _type:_ `{ptype}` — {truncate(desc, 200)}")
    elif name in ("TaskGet", "TaskList", "TaskOutput", "TaskStop"):
        tid = inp.get("task_id", inp.get("id", ""))
        if tid:
            lines.append(f"  _task_id:_ `{tid}`")
    elif name == "ToolSearch":
        q = inp.get("query", "")
        lines.append(f"  _query:_ `{q}`")
    else:
        # Generic: show first 2 key-value pairs
        items = list(inp.items())[:3]
        for k, v in items:
            v_str = str(v) if not isinstance(v, dict) else json.dumps(v)
            lines.append(f"  _{k}:_ `{truncate(v_str, 150)}`")

    return "\n".join(lines)

def render_tool_result(block: dict) -> str:
    content = block.get("content", "")
    is_error = block.get("is_error", False)

    if isinstance(content, list):
        # Sometimes content is a list of blocks
        parts = []
        for b in content:
            if isinstance(b, dict):
                parts.append(b.get("text", str(b)))
            else:
                parts.append(str(b))
        content = "\n".join(parts)

    label = "**Result** (error):" if is_error else "**Result:**"
    content_str = truncate(str(content))

    return f"{label}\n```\n{content_str}\n```"

def render_blocks(blocks) -> list[str]:
    """Render a list of content blocks to markdown strings."""
    parts = []

    if not blocks:
        return parts

    # Check if it's a string list (system context injection)
    if blocks and isinstance(blocks[0], str):
        full = "".join(blocks)
        # Skip pure local-command-caveat wrappers
        if "<local-command-caveat>" in full or "<system-reminder>" in full or "<parameter name=" in full:
            return []  # Skip system context injections
        # Otherwise show truncated
        parts.append(f"> _[context injection: {truncate(full, 200)}]_")
        return parts

    for block in blocks:
        if not isinstance(block, dict):
            # Raw string content
            parts.append(str(block))
            continue

        btype = block.get("type", "")

        if btype == "text":
            text = block.get("text", "")
            if text.strip():
                parts.append(text)

        elif btype == "thinking":
            thinking = block.get("thinking", "")
            if thinking and thinking.strip():
                # Render as collapsible details
                parts.append(f"<details>\n<summary>💭 <em>Thinking</em></summary>\n\n{thinking}\n\n</details>")
            else:
                # Empty thinking block (redacted)
                parts.append("> 💭 *[thinking — redacted/empty]*")

        elif btype == "tool_use":
            parts.append(render_tool_use(block))

        elif btype == "tool_result":
            parts.append(render_tool_result(block))

        else:
            # Unknown block type — show compact
            parts.append(f"> _[block type: {btype}]_")

    return parts

def is_system_context(record: dict) -> bool:
    """Return True if this user record is just a context injection."""
    msg = record.get("message", {})
    content = msg.get("content", [])
    if not content:
        return True
    if isinstance(content[0], str):
        return True  # String list = system context
    return False

def is_tool_result_only(record: dict) -> bool:
    """Return True if user record is only tool results (response to tool calls)."""
    msg = record.get("message", {})
    content = msg.get("content", [])
    if not content:
        return False
    return all(
        isinstance(b, dict) and b.get("type") == "tool_result"
        for b in content
    )

def main():
    print(f"Processing: {INPUT}", file=sys.stderr)

    # First pass: count records and gather session info
    total_records = 0
    first_ts = None
    last_ts = None
    session_ids = set()

    with open(INPUT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total_records += 1
            try:
                obj = json.loads(line)
                ts = obj.get("timestamp")
                if ts:
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts
                sid = obj.get("sessionId")
                if sid:
                    session_ids.add(sid)
            except json.JSONDecodeError:
                pass

    print(f"Total records: {total_records}", file=sys.stderr)

    # Second pass: render
    # We'll collect rendered turns as a list
    # A "turn" is a logical exchange: user message(s) + assistant response(s)

    out_lines = []

    # Header
    source_name = os.path.basename(INPUT)
    render_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out_lines.append(f"# Transcript: {source_name}")
    out_lines.append(f"")
    out_lines.append(f"| Field | Value |")
    out_lines.append(f"|---|---|")
    out_lines.append(f"| Source | `{source_name}` |")
    out_lines.append(f"| Records | {total_records:,} |")
    out_lines.append(f"| Session(s) | {', '.join(sorted(session_ids))} |")
    if first_ts:
        out_lines.append(f"| Start | {fmt_timestamp(first_ts)} |")
    if last_ts:
        out_lines.append(f"| End | {fmt_timestamp(last_ts)} |")
    out_lines.append(f"| Rendered | {render_date} |")
    out_lines.append(f"")
    out_lines.append(f"---")
    out_lines.append(f"")

    turn_count = 0
    last_rendered_role = None  # track what we last rendered
    pending_tool_results = []  # accumulate tool results before rendering
    seen_last_prompts: set[str] = set()  # deduplicate last-prompt records

    def flush_tool_results():
        nonlocal out_lines, pending_tool_results
        if not pending_tool_results:
            return
        out_lines.append("")
        for tr_text in pending_tool_results:
            out_lines.append(tr_text)
            out_lines.append("")
        pending_tool_results = []

    with open(INPUT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            rtype = obj.get("type", "")

            # === SKIP noise ===
            if rtype in ("mode", "file-history-snapshot", "attachment", "ai-title"):
                continue

            if rtype == "system":
                subtype = obj.get("subtype", "")
                # Skip pure local_command noise, turn_duration, stop_hook_summary
                if subtype in ("local_command", "turn_duration", "stop_hook_summary",
                               "internal", "cwd", "init"):
                    continue
                # Show other system records as a note
                content = obj.get("content", "")
                if content and content.strip() and content != "<local-command-stdout></local-command-stdout>":
                    flush_tool_results()
                    out_lines.append(f"> _[system/{subtype}]: {truncate(str(content), 200)}_")
                    out_lines.append("")
                continue

            if rtype == "queue-operation":
                # Operator queued a message — treat as user input
                content = obj.get("content", "")
                ts = obj.get("timestamp", "")

                # Skip empty
                if not content or not content.strip():
                    continue

                # Task notifications → fold as info line, not a user turn
                if "<task-notification>" in content:
                    # Extract summary
                    import re as _re
                    m = _re.search(r"<summary>(.*?)</summary>", content, _re.DOTALL)
                    task_id_m = _re.search(r"<task-id>(.*?)</task-id>", content)
                    status_m = _re.search(r"<status>(.*?)</status>", content)
                    summary = m.group(1).strip() if m else truncate(content, 150)
                    task_id = task_id_m.group(1).strip() if task_id_m else "?"
                    status = status_m.group(1).strip() if status_m else "?"
                    flush_tool_results()
                    out_lines.append(f"> 🔔 **Task notification** `{task_id}` [{status}]: {summary}")
                    out_lines.append("")
                    continue

                # Autonomous loop check → show as a brief info note
                if "# Autonomous loop check" in content or "Autonomous loop check" in content:
                    flush_tool_results()
                    out_lines.append(f"> ⏰ _[autonomous loop check — {fmt_timestamp(ts)}]_")
                    out_lines.append("")
                    continue

                flush_tool_results()
                out_lines.append(f"## 👤 User *(queued — {fmt_timestamp(ts)})*")
                out_lines.append("")
                out_lines.append(content)
                out_lines.append("")
                out_lines.append("---")
                out_lines.append("")
                turn_count += 1
                last_rendered_role = "user"
                continue

            if rtype == "pr-link":
                pr_num = obj.get("prNumber")
                pr_url = obj.get("prUrl", "")
                ts = obj.get("timestamp", "")
                flush_tool_results()
                out_lines.append(f"> 🔗 **PR #{pr_num} created** [{fmt_timestamp(ts)}]: {pr_url}")
                out_lines.append("")
                continue

            if rtype == "last-prompt":
                prompt = obj.get("lastPrompt", "")
                if prompt and prompt not in seen_last_prompts:
                    # Show as user message — deduplicated
                    seen_last_prompts.add(prompt)
                    flush_tool_results()
                    out_lines.append(f"## 👤 User *(prompt)*")
                    out_lines.append("")
                    out_lines.append(prompt)
                    out_lines.append("")
                    out_lines.append("---")
                    out_lines.append("")
                    turn_count += 1
                    last_rendered_role = "user"
                continue

            if rtype == "user":
                if is_system_context(obj):
                    continue  # Skip system context injections

                msg = obj.get("message", {})
                content = msg.get("content", [])
                ts = obj.get("timestamp", "")
                is_meta = obj.get("isMeta", False)

                if is_meta:
                    continue

                # Check if it's tool results only
                if is_tool_result_only(obj):
                    # Render tool results compactly, attributed to the previous tool call
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            pending_tool_results.append(render_tool_result(block))
                    continue

                # Real user message
                parts = render_blocks(content)
                if not parts:
                    continue

                flush_tool_results()
                out_lines.append(f"## 👤 User *({fmt_timestamp(ts)})*")
                out_lines.append("")
                for p in parts:
                    out_lines.append(p)
                out_lines.append("")
                out_lines.append("---")
                out_lines.append("")
                turn_count += 1
                last_rendered_role = "user"
                continue

            if rtype == "assistant":
                msg = obj.get("message", {})
                content = msg.get("content", [])
                ts = obj.get("timestamp", "")

                if not content:
                    continue

                # Determine content type(s)
                has_thinking = any(isinstance(b, dict) and b.get("type") == "thinking" for b in content)
                has_text = any(isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip() for b in content)
                has_tool_use = any(isinstance(b, dict) and b.get("type") == "tool_use" for b in content)

                # Skip if only empty thinking
                if not has_text and not has_tool_use and has_thinking:
                    # Check if thinking is empty
                    thinking_texts = [b.get("thinking", "") for b in content if isinstance(b, dict) and b.get("type") == "thinking"]
                    if all(not t.strip() for t in thinking_texts):
                        continue

                # If this is a tool_use only block (no text), accumulate pending results
                # and start a new assistant block
                flush_tool_results()

                if last_rendered_role != "assistant":
                    out_lines.append(f"## 🤖 Assistant *({fmt_timestamp(ts)})*")
                    out_lines.append("")
                    turn_count += 1
                    last_rendered_role = "assistant"

                parts = render_blocks(content)
                for p in parts:
                    out_lines.append(p)
                    out_lines.append("")

                # After tool_use blocks, we expect tool results next — don't add separator yet
                if not has_tool_use:
                    out_lines.append("---")
                    out_lines.append("")
                    last_rendered_role = None  # Allow next assistant to start fresh

                continue

    # Flush any remaining tool results
    flush_tool_results()

    # Write output
    output_text = "\n".join(out_lines)
    with open(OUTPUT, "w") as f:
        f.write(output_text)

    print(f"Done. Turns rendered: {turn_count}", file=sys.stderr)
    print(f"Output: {OUTPUT}", file=sys.stderr)
    print(f"Output size: {len(output_text):,} bytes", file=sys.stderr)

    return turn_count, len(output_text)

if __name__ == "__main__":
    main()
