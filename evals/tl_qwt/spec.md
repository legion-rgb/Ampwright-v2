# tl_qwt: quarter-wave transformer, 50 to 100 Ohm at 2 GHz

Task: match port 1 (50 Ohm) to port 2 (100 Ohm) at 2 GHz with one ideal quarter-wave line (TLIN). Theory picks Z0 and the length.

Known answer: Z0 = 70.71 Ohm, 90 deg at 2 GHz. The |S11| null is at 2 GHz, |S11| is -9.54 dB at 4 GHz and -23.2 dB at 1.75 and 2.25 GHz. The -20 dB fractional bandwidth is 36.7%.

Sweep: 0.5 to 7 GHz, with 2 GHz and 4 GHz as exact points. Set it on the schematic only, with `document=v2_tl_qwt`.

Documents: schematic `v2_tl_qwt`, and graph `v2_tl_qwt_s` holding `DB(|S(1,1)|)` only.

Approved by the user: 21 Nov 2026 (eval task).
