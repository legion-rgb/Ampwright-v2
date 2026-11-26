# fn_rc_check report (26 Nov 2026)

**Verdict: PASS in round 0.** First full agent loop started from a Fieldnote Design-mode spec.

## Spec
First-order RC low-pass with a 1 GHz -3 dB cutoff (3 dB below the DC level), 50 Ohm ports, ideal lumped RES and CAP. The user approved it on 26 Nov. Details are in `spec.md`.

## Final values
| part | value |
|---|---|
| R1 (series) | 50 Ohm |
| C1 (shunt) | 4.775 pF |
| P1, P2 | 50 Ohm |

Sweep: 10 MHz to 10 GHz in 10 MHz steps, set on `v2_fn_rc_check` only. Documents: `v2_fn_rc_check` and `v2_fn_rc_check_s`.

## Verdict table
| goal | spec | theory | measured | result |
|---|---|---|---|---|
| s21_dc (10 MHz) | -3.52 +/- 0.05 dB | -3.522 | -3.5223 | pass |
| s21_fc (1 GHz) | -6.53 +/- 0.25 dB | -6.532 | -6.5324 | pass |
| s21_stop (10 GHz) | <= -22 dB | -23.57 | -23.5657 | pass |

## Rounds
theory -> build -> evaluate -> judge PASS (round 0) -> review (no MUST) -> report. No fixer.

## Open points
- A matching `v2_fn_rc_check` and `v2_fn_rc_check_s` were already in AWR before the build, and nothing in the dossier made them. They probably come from the 25 Nov live Design-mode test, even though that log says there were no AWR writes. The builder deleted the elements, rebuilt them in place, and re-added the measurement.
- Bash was denied for the evaluator, so `checks/check_spec.py` and `check_tidy.py` didn't run. The values came from `graph_data` (the full 1000-point trace, with exact points at every goal frequency), and tidiness was judged from `list_wires`.
- Not saved (user instruction).
