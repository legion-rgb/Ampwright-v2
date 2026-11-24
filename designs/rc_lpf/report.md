# rc_lpf report

Spec: series 50 Ohm R, shunt C, 50 Ohm ports, corner at 10 MHz (user-approved 21 Nov 2026).
Final values: R1 = 50 Ohm, C1 = 477.5 pF. Documents: `v2_rc_lpf`, `v2_rc_lpf_s`. Not saved.

| Goal | Spec | Predicted | Measured | Verdict |
|---|---|---|---|---|
| s21_dc @ 100 kHz | -3.52 +/- 0.05 dB | -3.522 | -3.522 | PASS |
| s21_fc @ 10 MHz | -6.53 +/- 0.25 dB | -6.532 | -6.532 | PASS |
| s21_stop @ 100 MHz | <= -22 dB | -23.566 | -23.566 | PASS |

Rounds: 0 fixes. Review: no MUST findings, check_tidy ok.
Open: results.json says "interpolation" even at exact sweep points (cosmetic).
Next: seeded-fault test (PROGRESS step 6), see seed.md once run.

## Seeded-fault test (PROGRESS step 6, 21 Nov)
The lead had C1 set to 4775 pF (10x), recorded only in `designs/_seeds/rc_lpf.md`.
- Round 1: the Evaluator flagged s21_fc at -23.57 dB. The Judge gave FAIL and found C1 = 4775 pF against 477.5 pF in build_log.md.
- Fix: the Fixer set C1 back to 477.5 pF (as the SI number 4.775e-10; the string '477.5' landed as 477.5 F, see playbook). It re-simulated.
- Recheck: the Evaluator and the Judge both gave PASS on all 3 goals, within 0.001 dB of theory; check_tidy ok.
Caught and fixed in 1 round (target: 2 or fewer).
