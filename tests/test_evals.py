"""evals/score.py on made-up dossiers, no AWR. Run: python tests/test_evals.py"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "evals"))
import score  # noqa: E402

tmp = tempfile.mkdtemp()
try:
    def dossier(task, phase, rnd, verdict, meets):
        d = os.path.join(tmp, task)
        os.makedirs(d)
        goals = [g["id"] for g in json.load(open(os.path.join(ROOT, "evals", task, "spec.json")))["goals"]]
        json.dump({"phase": phase, "round": rnd}, open(os.path.join(d, "state.json"), "w"))
        json.dump({"_sim": "ok", **{g: {"meets": meets} for g in goals}}, open(os.path.join(d, "results.json"), "w"))
        open(os.path.join(d, "verdict.md"), "w").write(f"# x\n**VERDICT: {verdict}**\n")

    dossier("rc_lpf", "pass", 0, "PASS", True)
    dossier("rc_lpf_fault", "pass", 3, "PASS", True)  # too many rounds
    dossier("tl_qwt", "fix", 1, "FAIL", False)
    os.makedirs(os.path.join(tmp, "rlc_notch"))  # started, no files yet
    assert score.score("rc_lpf", tmp) == ("OK", 0)
    assert score.score("rc_lpf_fault", tmp) == ("FAIL: 3 rounds > 2", 3)
    s, _ = score.score("tl_qwt", tmp)
    assert "phase 'fix'" in s and "verdict not PASS" in s and "goals not all met" in s, s
    assert score.score("rlc_notch", tmp)[0].startswith("incomplete")
    assert score.score("ne3508_bias", tmp) == ("not run", None)
    assert score.main(["score", tmp]) == 1
finally:
    shutil.rmtree(tmp)
print("OK")

# fix_uses: lmatch_opt only scores OK when fix_log.md shows the optimizer was used
import tempfile as _tf
_d = _tf.mkdtemp()
_t = os.path.join(_d, "lmatch_opt")
os.makedirs(_t)
json.dump({"phase": "pass", "round": 1}, open(os.path.join(_t, "state.json"), "w"))
json.dump({"_sim": "ok", "s11_f0": {"meets": True}, "s11_band": {"meets": True}}, open(os.path.join(_t, "results.json"), "w"))
open(os.path.join(_t, "verdict.md"), "w").write("VERDICT: PASS")
assert "run_optimizer" in score.score("lmatch_opt", _d)[0], score.score("lmatch_opt", _d)
open(os.path.join(_t, "fix_log.md"), "w").write("Change: run_optimizer, Simplex, cost 40 -> 0")
assert score.score("lmatch_opt", _d) == ("OK", 1), score.score("lmatch_opt", _d)
print("OK fix_uses")
