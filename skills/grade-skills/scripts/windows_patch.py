"""Monkey-patch skill-creator's run_eval. **Filename is historical** — the
module originally only fixed Windows-specific issues but now also fixes a
platform-independent skill-discovery collision. Apply on every platform.

Three problems with the upstream implementation:
1. (Windows-only) `select.select()` on subprocess pipes is not supported —
   Windows select() only works on sockets. The read loop in run_single_query
   never receives any data, so every query returns False (never triggered).
2. (Windows-only) ProcessPoolExecutor with spawn semantics crashes under
   parallel claude -p load (WinError 10038 / "child process terminated abruptly").
3. (**All platforms**) The upstream harness writes a synthetic command file
   into the *real* project's `.claude/commands/` directory and runs `claude -p`
   with cwd=real project. On any project that already has the skill being
   graded installed in `.claude/skills/`, the subprocess Claude sees BOTH the
   real skill and the synthetic command file — and picks the real one. The
   harness then checks for the synthetic UUID-suffixed name in the tool input,
   doesn't find it, and records False. Every should-trigger query is
   misclassified → recall = 0% uniformly across all skills.

Fix: replace run_single_query with a thread-based reader that runs `claude -p`
in an **isolated temporary project root** containing only the synthetic skill.
This satisfies Claude's skill discovery (via `.claude/skills/`, not commands/),
removes competition from real skills, and yields true trigger signals. Also
swap ProcessPoolExecutor → ThreadPoolExecutor in run_eval. The thread-based
reader and ThreadPoolExecutor work cross-platform — the POSIX `select()` path
in the upstream code was an optimization, not a requirement. Applied by
importing this module before importing run_loop.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _patched_run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None = None,
) -> bool:
    """Thread-safe replacement for run_single_query.

    Runs `claude -p` in an isolated temp project root that contains ONLY the
    synthetic skill under test. This is the only way to get a clean trigger
    signal when the project already has the real skill installed (or any other
    skill whose description overlaps with this one's queries) — otherwise
    Claude triggers the real skill and the harness records False.

    The `project_root` argument is unused but kept for API compatibility with
    the upstream `run_single_query` signature that this function replaces.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"

    # Isolated temp project root — only the synthetic skill is visible to claude -p
    tmp_root = Path(tempfile.mkdtemp(prefix="skill_eval_"))
    synthetic_skill_dir = tmp_root / ".claude" / "skills" / clean_name
    process = None

    try:
        synthetic_skill_dir.mkdir(parents=True, exist_ok=True)
        indented_desc = "\n  ".join(skill_description.split("\n"))
        # SKILL.md frontmatter — keep it minimal but valid.
        (synthetic_skill_dir / "SKILL.md").write_text(
            f"---\nname: {clean_name}\ndescription: |\n  {indented_desc}\n---\n\n"
            f"# {clean_name}\n\nThis skill handles: {skill_description}\n",
            encoding="utf-8",
        )

        cmd = ["claude", "-p", query, "--output-format", "stream-json",
               "--verbose", "--include-partial-messages"]
        if model:
            cmd.extend(["--model", model])

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(tmp_root),
            env=env,
        )

        # Feed lines from stdout into a queue via a reader thread —
        # avoids select() which is unusable on Windows pipes.
        line_queue: queue.Queue[str | None] = queue.Queue()

        def _reader():
            try:
                for raw in process.stdout:
                    line_queue.put(raw.decode("utf-8", errors="replace").rstrip())
            finally:
                line_queue.put(None)  # sentinel

        threading.Thread(target=_reader, daemon=True).start()

        triggered = False
        pending_tool_name = None
        accumulated_json = ""
        deadline = time.time() + timeout

        while time.time() < deadline:
            try:
                line = line_queue.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                break
            if line is None:
                break
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "stream_event":
                se = event.get("event", {})
                se_type = se.get("type", "")

                if se_type == "content_block_start":
                    cb = se.get("content_block", {})
                    if cb.get("type") == "tool_use":
                        tool_name = cb.get("name", "")
                        if tool_name in ("Skill", "Read"):
                            pending_tool_name = tool_name
                            accumulated_json = ""
                        else:
                            return False

                elif se_type == "content_block_delta" and pending_tool_name:
                    delta = se.get("delta", {})
                    if delta.get("type") == "input_json_delta":
                        accumulated_json += delta.get("partial_json", "")
                        if clean_name in accumulated_json:
                            return True

                elif se_type in ("content_block_stop", "message_stop"):
                    if pending_tool_name:
                        return clean_name in accumulated_json
                    if se_type == "message_stop":
                        return False

            elif event.get("type") == "assistant":
                for item in event.get("message", {}).get("content", []):
                    if item.get("type") != "tool_use":
                        continue
                    tool_name = item.get("name", "")
                    tool_input = item.get("input", {})
                    if tool_name == "Skill" and clean_name in tool_input.get("skill", ""):
                        triggered = True
                    elif tool_name == "Read" and clean_name in tool_input.get("file_path", ""):
                        triggered = True
                    return triggered

            elif event.get("type") == "result":
                return triggered

        return triggered

    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        # Always clean up the isolated temp project root
        try:
            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass


def _patched_run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: "Path",
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Replacement for run_eval using ThreadPoolExecutor (safe on Windows)."""
    results = []

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    _patched_run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        did_pass = (trigger_rate >= trigger_threshold) if should_trigger else (trigger_rate < trigger_threshold)
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {"total": total, "passed": passed, "failed": total - passed},
    }


def apply() -> None:
    """Patch scripts.run_eval in-place. Call before importing run_loop."""
    import scripts.run_eval as _run_eval_mod  # noqa: PLC0415

    _run_eval_mod.run_single_query = _patched_run_single_query
    _run_eval_mod.run_eval = _patched_run_eval

    # run_loop imports run_eval at module level — patch its reference too
    try:
        import scripts.run_loop as _run_loop_mod  # noqa: PLC0415
        _run_loop_mod.run_eval = _patched_run_eval
    except ImportError:
        pass
