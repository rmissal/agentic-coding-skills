#!/usr/bin/env python3
"""Grade + auto-improve all skills that have evals/queries.json.

For each skill:
  1. Runs the eval+improve loop from skill-creator — improves description if score < 100%
  2. Saves evals/grades.json with per-query pass/fail + best description found
  3. If best description differs from current, patches SKILL.md in-place

Also writes grades_summary.json in the skills-root directory.

Usage (from any directory):
    PYTHONUTF8=1 py <path-to-this-script> --skills-root <path-to-.claude/skills> [options]

The script locates skill-creator automatically as a sibling of skills-root/../skill-creator.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def _add_skill_creator_to_path(skills_root: Path) -> None:
    """Add skill-creator to sys.path so we can import run_loop and utils."""
    skill_creator = skills_root / "skill-creator"
    if not skill_creator.is_dir():
        raise RuntimeError(
            f"skill-creator not found at {skill_creator}. "
            "Run setup.sh first to install it."
        )
    # Also add grade-skills itself so windows_patch.py is importable
    grade_skills_scripts = Path(__file__).parent
    for p in [str(skill_creator), str(grade_skills_scripts)]:
        if p not in sys.path:
            sys.path.insert(0, p)


def patch_skill_description(skill_path: Path, new_description: str) -> bool:
    """Replace the description field in SKILL.md frontmatter. Returns True if changed."""
    skill_md = skill_path / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")

    fm_match = re.match(r"^(---\n)(.*?)(\n---)", content, re.DOTALL)
    if not fm_match:
        return False

    fm_text = fm_match.group(2)

    new_fm = re.sub(
        r"(description:\s*).*?(?=\n\S|\Z)",
        lambda m: m.group(1) + new_description,
        fm_text,
        count=1,
        flags=re.DOTALL,
    )

    if new_fm == fm_text:
        return False

    new_content = content[: fm_match.start(2)] + new_fm + content[fm_match.end(2) :]
    skill_md.write_text(new_content, encoding="utf-8")
    return True


def grade_and_improve_skill(
    skill_path: Path,
    num_workers: int,
    timeout: int,
    runs_per_query: int,
    max_iterations: int,
    trigger_threshold: float,
    holdout: float,
    model: str,
    verbose: bool,
) -> dict:
    # Late imports — sys.path was extended by _add_skill_creator_to_path before main() ran
    from scripts.run_loop import run_loop  # noqa: PLC0415

    queries_file = skill_path / "evals" / "queries.json"
    eval_set = json.loads(queries_file.read_text(encoding="utf-8"))

    return run_loop(
        eval_set=eval_set,
        skill_path=skill_path,
        description_override=None,
        num_workers=num_workers,
        timeout=timeout,
        max_iterations=max_iterations,
        runs_per_query=runs_per_query,
        trigger_threshold=trigger_threshold,
        holdout=holdout,
        model=model,
        verbose=verbose,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grade + auto-improve all skills with evals/queries.json"
    )
    parser.add_argument("--skills-root", required=True, help="Path to .claude/skills/ directory")
    parser.add_argument("--num-workers", type=int, default=8, help="Parallel workers per skill")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds")
    parser.add_argument("--runs-per-query", type=int, default=1, help="Runs per query (1 = quick grade)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max improvement iterations per skill")
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    parser.add_argument(
        "--holdout",
        type=float,
        default=0.0,
        help="Holdout fraction for test split (0 = use all for training)",
    )
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="Model for eval+improve")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--parallel-skills", type=int, default=1,
        help="Number of skills to grade in parallel (default: 1 = sequential). "
             "Set to 2-4 to grade multiple skills concurrently. "
             "Note: each skill also runs --num-workers queries in parallel, so "
             "total concurrent claude -p calls = parallel-skills × num-workers.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip skills that already have a grades.json",
    )
    args = parser.parse_args()

    skills_root = Path(args.skills_root).resolve()
    _add_skill_creator_to_path(skills_root)

    # Apply the eval-harness patch before run_loop is imported. This patch fixes
    # THREE problems, two Windows-specific (select() on pipes, ProcessPoolExecutor
    # crashes) AND one platform-independent: the skill-discovery collision that
    # makes claude -p trigger the real installed skill instead of the synthetic
    # one — producing uniform recall=0% on every grading run. The collision
    # affects Linux/macOS just as much as Windows, so the patch must apply
    # unconditionally. The two Windows-specific fixes (thread-based reader,
    # ThreadPoolExecutor) are no-ops on POSIX but do no harm.
    from windows_patch import apply as _apply_eval_patch  # noqa: PLC0415
    _apply_eval_patch()

    skill_dirs = sorted(
        p.parent.parent
        for p in skills_root.glob("*/evals/queries.json")
    )

    if not skill_dirs:
        print("No skills with queries.json found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(skill_dirs)} skills to grade.", file=sys.stderr)

    summary_rows: list[dict] = []
    failed_skills: list[str] = []

    # Separate into skip vs work lists upfront
    to_grade = []
    for i, skill_path in enumerate(skill_dirs, 1):
        grades_file = skill_path / "evals" / "grades.json"
        if args.skip_existing and grades_file.exists():
            existing = json.loads(grades_file.read_text(encoding="utf-8"))
            print(f"[{i}/{len(skill_dirs)}] SKIP {skill_path.name} (grades.json exists)", file=sys.stderr)
            summary_rows.append({
                "skill": existing.get("skill", skill_path.name),
                "best_score": existing.get("best_score", "?"),
                "improved": False,
                "skipped": True,
            })
        else:
            to_grade.append((i, skill_path))

    def _grade_one(job: tuple[int, Path]) -> tuple[int, Path, dict | None, Exception | None]:
        i, skill_path = job
        print(f"\n[{i}/{len(skill_dirs)}] {skill_path.name}", file=sys.stderr)
        t0 = time.time()
        try:
            result = grade_and_improve_skill(
                skill_path=skill_path,
                num_workers=args.num_workers,
                timeout=args.timeout,
                runs_per_query=args.runs_per_query,
                max_iterations=args.max_iterations,
                trigger_threshold=args.trigger_threshold,
                holdout=args.holdout,
                model=args.model,
                verbose=args.verbose,
            )
            result["_elapsed"] = time.time() - t0
            return i, skill_path, result, None
        except Exception as exc:
            return i, skill_path, None, exc

    parallel = max(1, args.parallel_skills)
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {pool.submit(_grade_one, job): job for job in to_grade}
        for future in as_completed(futures):
            i, skill_path, result, exc = future.result()
            grades_file = skill_path / "evals" / "grades.json"

            if exc is not None:
                elapsed = 0.0
                print(f"[{i}/{len(skill_dirs)}] ERROR {skill_path.name}: {exc} ({elapsed:.1f}s)", file=sys.stderr)
                failed_skills.append(skill_path.name)
                summary_rows.append({"skill": skill_path.name, "best_score": "error", "improved": False, "error": str(exc), "skipped": False})
                continue

            elapsed = result.pop("_elapsed", 0.0)
            best_score = result.get("best_score", "?")
            original_desc = result.get("original_description", "")
            best_desc = result.get("best_description", original_desc)
            final_desc = result.get("final_description", best_desc)

            # Only treat as "improved" if the best description scored STRICTLY
            # higher than iteration 1 (the original). When the eval harness can't
            # discriminate (e.g. all iterations score identically), iteration 1's
            # description wins by max() tie-break and best_desc == original_desc.
            # Patching SKILL.md based on iteration N text alone, with no measurable
            # improvement, regresses descriptions and is exactly what produced the
            # bad patches that motivated this fix.
            history = result.get("history", [])
            first_score = history[0].get("train_passed", 0) if history else 0
            best_passed = max((h.get("train_passed", 0) for h in history), default=0)
            improved = (best_desc != original_desc) and (best_passed > first_score)

            print(
                f"[{i}/{len(skill_dirs)}] {skill_path.name}: score={best_score}"
                + (" [IMPROVED]" if improved else "")
                + f" in {elapsed:.1f}s",
                file=sys.stderr,
            )

            best_history = max(result.get("history", [{}]), key=lambda h: h.get("train_passed", 0))
            summary = {"passed": best_history.get("train_passed", 0), "failed": best_history.get("train_failed", 0), "total": best_history.get("train_total", 0)}

            grades = {
                "skill": skill_path.name,
                "best_score": best_score,
                "original_description": original_desc,
                "best_description": best_desc,
                "final_description": final_desc,
                "improved": improved,
                "iterations_run": result.get("iterations_run", 1),
                "exit_reason": result.get("exit_reason", ""),
                "elapsed_seconds": round(elapsed, 1),
                "summary": summary,
                "history": result.get("history", []),
            }
            grades_file.write_text(json.dumps(grades, indent=2), encoding="utf-8")

            if improved:
                patched = patch_skill_description(skill_path, best_desc)
                if patched:
                    print(f"  -> Patched SKILL.md with improved description (score {first_score} -> {best_passed})", file=sys.stderr)

            summary_rows.append({
                "skill": skill_path.name,
                "best_score": best_score,
                "improved": improved,
                "iterations_run": result.get("iterations_run", 1),
                "skipped": False,
            })

    improved_count = sum(1 for r in summary_rows if r.get("improved"))
    summary = {
        "graded": len([r for r in summary_rows if not r.get("skipped") and not r.get("error")]),
        "improved": improved_count,
        "failed_to_run": len(failed_skills),
        "skills": summary_rows,
    }

    summary_file = skills_root / "grades_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n=== DONE ===", file=sys.stderr)
    print(f"Graded: {summary['graded']}, Improved: {improved_count}, Errors: {len(failed_skills)}", file=sys.stderr)
    if failed_skills:
        print(f"Errors: {', '.join(failed_skills)}", file=sys.stderr)
    print(f"Summary: {summary_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
