"""Score agent eval runs. python evals/score.py [designs_dir]
Each evals/<task>/ holds spec.md, spec.json (the known answers) and eval.json (max_rounds, optional seed).
A run's dossier is designs/<task>/. A task scores OK when state.json phase is "pass", verdict.md says PASS,
results.json meets every goal, and state.json round <= max_rounds. Exit 1 unless every task is OK."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(path):
    return json.load(open(path, encoding="utf-8-sig"))


def score(task, designs):
    ev = _load(os.path.join(HERE, task, "eval.json"))
    d = os.path.join(designs, task)
    if not os.path.isdir(d):
        return "not run", None
    try:
        st = _load(os.path.join(d, "state.json"))
        res = _load(os.path.join(d, "results.json"))
        verdict = open(os.path.join(d, "verdict.md"), encoding="utf-8").read()
    except (OSError, ValueError) as e:
        return f"incomplete ({type(e).__name__})", None
    goals = [g["id"] for g in _load(os.path.join(HERE, task, "spec.json"))["goals"]]
    rounds = st.get("round", 0)
    why = []
    if st.get("phase") != "pass":
        why.append(f"phase {st.get('phase')!r}")
    if not re.search(r"VERDICT:\W*PASS", verdict):
        why.append("verdict not PASS")
    if res.get("_sim") != "ok" or not all(res.get(g, {}).get("meets") for g in goals):
        why.append("goals not all met")
    if rounds > ev["max_rounds"]:
        why.append(f"{rounds} rounds > {ev['max_rounds']}")
    if ev.get("fix_uses"):  # the fix must have used this tool, e.g. run_optimizer
        log = open(os.path.join(d, "fix_log.md"), encoding="utf-8").read() if os.path.exists(os.path.join(d, "fix_log.md")) else ""
        if ev["fix_uses"] not in log:
            why.append(f"fix_log.md never mentions {ev['fix_uses']}")
    return ("OK" if not why else "FAIL: " + ", ".join(why)), rounds


def cost(task, designs):
    """'$1.23, 40 turns' from a headless run's headless.json, or '' when the run was interactive."""
    p = os.path.join(designs, task, "headless.json")
    if not os.path.exists(p):
        return ""
    h = _load(p)
    return f"${h.get('total_cost_usd') or 0:.2f}, {h.get('num_turns')} turns"


def main(argv):
    designs = argv[1] if len(argv) > 1 else os.path.join(HERE, "..", "designs")
    tasks = sorted(t for t in os.listdir(HERE) if os.path.isfile(os.path.join(HERE, t, "eval.json")))
    rows = [(t, *score(t, designs)) for t in tasks]
    for t, s, r in rows:
        print(f"{t:14} rounds={'-' if r is None else r}  {s}  {cost(t, designs)}".rstrip())
    ok = sum(s == "OK" for _, s, _ in rows)
    print(f"{ok}/{len(rows)} OK")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
