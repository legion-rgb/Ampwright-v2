# Report: rc_lpf_fault (eval task, 21 Nov 2026)

Spec: 1st-order RC low-pass between 50 Ohm ports, corner at 10 MHz (spec.md, approved as an eval task).
Final values: R1 = 50 Ohm, C1 = `4.775*100` pF (477.5 pF). Built at 477 pF; the fixer restored the value as 477.5 pF.

| goal | spec | theory | round 0 | round 1 (seeded) | round 1 fixed |
|---|---|---|---|---|---|
| s21_dc, 100 kHz | -3.52 +/- 0.05 | -3.52 | -3.522 | -3.565 | -3.522 |
| s21_fc, 10 MHz | -6.53 +/- 0.25 | -6.53 | -6.528 | **-23.57 FAIL** | -6.532 |
| s21_stop, 100 MHz | <= -22 | -23.55 | -23.557 | -43.52 | -23.566 |

Rounds: round 0 PASS. Then the lead seeded a 10x C1 fault (4775 pF), without telling the agents. The Evaluator and Judge failed s21_fc, and the Judge named C1 at 10x as the cause. The fixer made one change and the design re-PASSED, in 1 of 2 allowed rounds. The review had no MUST findings.

Open points:
- The sweep starts at 100 kHz, not the spec's 10 kHz. This is documented, and no goal is affected.
- Planting the seed took 4 tries. Each failure showed a part-value trap (see playbook Units and `designs/_probes/param_units.md`): "4775 pF" fails to simulate, and 4.775e-9 arrived as text, so AWR read it as pF.
