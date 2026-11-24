# cheb5_lpf MSTEP sensitivity check: BLOCKED (model limit)

Schematic `v2_cheb5_lpf_mstep` (own MSUB `v2_MSUB2`, same values as v2_MSUB: Er 4.4, H 800 um, T 35 um, Rho 1, Tand 0.02). Sweep 0.1-6 GHz, 10 MHz (591 pts). Graph `v2_cheb5_lpf_mstep_s` (DB(|S(2,1)|), DB(|S(1,1)|)). v2_cheb5_lpf and its graph untouched.

## Parts (read back)
- TL1, TL5: MLIN W 5500 um, L 6050 um. TL2, TL4: W 215 um, L 8650 um. TL3: W 5500 um, L 10000 um. All MSUB v2_MSUB2.
- S1 MSTEP W1 5500 / W2 215 um; S2 MSTEP W1 215 / W2 5500; S3 MSTEP 5500 / 215; S4 MSTEP 215 / 5500 (all MSUB v2_MSUB2).
- No MSTEP at the ports: the port feed is the 5500 um line (not 50 Ohm-wide).
- P1 on TL1:1, P2 on TL5:1 (Z 50). TL5 is traversed pin 2 to pin 1 (symmetric line), layout wraps to a second row, no crossings.
- Chain: P1-TL1-S1-TL2-S2-TL3-S3-TL4-S4-TL5-P2.

## Result
Simulation fails: `MSTEP.S1 : W2/W1=0.0390909, must be >= 0.05`. The closed-form MSTEP cannot model the 215/5500 um ratio (0.039), so there are no goal values.

Alternatives (not tried): MSTEP2 (obsolete mode-matching, may have no ratio limit), MSTEPX (EM-based, slow), or widening the narrow line to W >= 275 um and retuning.

## Second try, MSTEPX (22 Nov): stopped by the user
The lead stopped the check at the user's request ("stop the MSTEPX check"), before the EM-based MSTEPX simulation ran, so no EM license was used. AWR then showed no open project. Result: step effects are still unmeasured.
