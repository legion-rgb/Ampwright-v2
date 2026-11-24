# lmatch_opt: lumped L-section match, 50 to 12.5 Ohm at 1 GHz

Task: match port 1 (50 Ohm) to port 2 (12.5 Ohm) at 1 GHz with one shunt C at port 1 and one series L toward port 2. Use ideal CAP and IND parts. Theory picks the values.

Known answer: Q = sqrt(50/12.5 - 1) = 1.732. C = Q/(w*50) = 5.513 pF and L = Q*12.5/w = 3.446 nH. |S11| is a null at 1 GHz, -17.0 dB at 0.9 GHz and -16.2 dB at 1.1 GHz.

Sweep: 0.5 to 1.5 GHz in 10 MHz steps, so 0.9, 1.0 and 1.1 GHz are sweep points. Set it on the schematic only, with `document=v2_lmatch_opt`.

Documents: schematic `v2_lmatch_opt`, and graph `v2_lmatch_opt_s` holding `DB(|S(1,1)|)` only.

Approved by the user: 21 Nov 2026 (eval task, part of "go with E.1 optimizer tools").
