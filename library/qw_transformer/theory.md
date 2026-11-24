# tl_qwt theory
Topology: one ideal TLIN between PORT1 (50 Ohm) and PORT2 (100 Ohm). Rejected: L-section (narrower, lumped, needs 2 parts), two-section transformer (not asked), tapered line (long).
Z0 = sqrt(50*100) = 70.7107 Ohm. Length 90 deg at 2 GHz = pi/2 = 1.5707963 rad.
Gamma(f): Zin = Z0 (ZL + jZ0 tan t)/(Z0 + jZL tan t), t = 90deg*f/2GHz; S11 = (Zin-50)/(Zin+50).
Results: 2 GHz null; 1.75/2.25 GHz -23.2 dB; 4 GHz (t=180) Zin=100 -> 1/3 -> -9.54 dB.
## AWR parameters (TLIN)
Z0 = 70.7106781 ; EL = 1.5707963 (radians) ; F0 = 2e9 (Hz). PORT1 Z=50, PORT2 Z=100 (port impedances must be set).
Models: TLIN, PORT (x2). No MSUB needed. Sweep 0.5-7 GHz, step e.g. 0.25 GHz so 2 and 4 GHz are exact points.
Assumption: lossless; f0 is the TLIN reference frequency for EL.
