"""Run eval tasks unattended with `claude -p` (AGENTIC_PLAN E.6), one at a time, then score them.
python evals/run_headless.py [task ...] [--budget 5] [--dry-run]
No task names = every task with no dossier yet. A task whose designs/<task>/ exists is skipped (move it away to rerun).
Each run's cost, turns and token use land in designs/<task>/headless.json. The guard hooks still apply: in -p mode
a save is never approved, and non-v2_* documents are refused. Needs a fresh untitled AWR project that nobody else is using."""
import glob
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
ALLOWED = ["mcp__Ampwright", "Read", "Write", "Edit", "Glob", "Grep", "Bash", "Agent"]
PROMPT = ("Run agent eval task {t} as evals/README.md describes: copy evals/{t}/spec.md and spec.json into designs/{t}/, "
          "then run the design loop in CLAUDE.md. The spec is pre-approved, so don't stop at step 2. Follow eval.json "
          "(seed, max rounds). Never save the AWR project. Finish with designs/{t}/report.md and state.json.")


def find_claude():
    hits = sorted(glob.glob(os.path.expanduser(r"~\.vscode\extensions\anthropic.claude-code-*\resources\native-binary\claude.exe")))
    return hits[-1] if hits else shutil.which("claude")  # shortcut: lexical sort, not semver (same as desktop_app)


def command(claude, task, budget):
    return [claude, "-p", PROMPT.format(t=task), "--output-format", "json", "--max-budget-usd", str(budget),
            "--allowedTools", *ALLOWED]


def tasks_to_run(names):
    every = sorted(t for t in os.listdir(HERE) if os.path.isfile(os.path.join(HERE, t, "eval.json")))
    unknown = set(names) - set(every)
    if unknown:
        sys.exit(f"unknown tasks: {sorted(unknown)}")
    return [t for t in (names or every) if not os.path.exists(os.path.join(ROOT, "designs", t))]


def main(argv):
    dry = "--dry-run" in argv
    budget = float(argv[argv.index("--budget") + 1]) if "--budget" in argv else 5.0
    names = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] != "--budget"]
    claude = find_claude()
    if not claude:
        sys.exit("claude.exe not found")
    for t in tasks_to_run(names):
        cmd = command(claude, t, budget)
        print(f"== {t}: {subprocess.list2cmdline(cmd[:2])} ...")
        if dry:
            continue
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        try:
            out = json.loads(p.stdout)
        except ValueError:
            out = {"error": "no JSON from claude", "returncode": p.returncode, "stderr": p.stderr[-2000:]}
        os.makedirs(os.path.join(ROOT, "designs", t), exist_ok=True)
        keep = {k: out.get(k) for k in ("total_cost_usd", "num_turns", "duration_ms", "usage", "is_error", "error", "stderr")}
        json.dump(keep, open(os.path.join(ROOT, "designs", t, "headless.json"), "w"), indent=1)
        print(f"   cost ${keep['total_cost_usd']}, turns {keep['num_turns']}, error {keep['is_error'] or keep['error']}")
    sys.path.insert(0, HERE)
    import score
    return score.main([""])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
