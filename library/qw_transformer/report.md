# Report: tl_qwt (eval task, 21 Nov 2026)

Spec: one ideal quarter-wave TLIN matching 50 to 100 Ohm at 2 GHz (spec.md, approved as an eval task).
Final values: TL1 Z0 = 70.7106781 Ohm, EL = 90 Deg, F0 = 2 GHz. P1 = 50 Ohm, P2 = 100 Ohm. Sweep 0.5-7 GHz, 0.25 GHz step.

| goal | spec | theory | measured | result |
|---|---|---|---|---|
| s11_f0, 2 GHz | <= -40 dB | <= -100 (ideal null) | -191.6 | PASS |
| s11_band, 1.75-2.25 GHz | <= -20 dB | -23.2 | -23.25 | PASS |
| s11_2f0, 4 GHz | -9.54 +/- 0.1 | -9.54 | -9.542 | PASS |

Rounds: PASS in round 0, with no fix. Review: no MUST findings, and the tidy check is ok.

Open points:
- The builder sent EL as the text '90', not radians. That works on the old server (display units) but not after the server fix ('90' would be 90 rad). playbook.md line 32 now says to send radians as a number.
- No goal checks the -20 dB bandwidth figure (36.7%). The judge confirmed the 3 band points are enough for this monotonic response.
