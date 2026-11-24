# Seeded fault: rc_lpf_fault (lead only)

21 Nov 2026, after the round-0 PASS: awr-builder sets C1 C = 4.775e-9 (10x the 477 pF) in v2_rc_lpf_fault and re-simulates. Not written in the dossier. Expected: the Evaluator and Judge FAIL round 1 and the fixer restores about 477 pF.

First attempt passed 4.775e-9 as text; AWR read it as 4.775e-9 pF (an open C). Redone as the string "4775 pF".
Planted on the 4th try as the expression "4.775*1000" (pF). Read back 4.775*1000 pF. S21 at 10 MHz is -23.566 dB, which matches 2/|3+j30|.
