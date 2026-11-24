# tl_qwt review
MUST: none.
Tidy: check_tidy.py ok, 0 issues. Two straight horizontal wires (P1-TL1, TL1-P2), no crossings, none over bodies.
Naming: v2_tl_qwt and graph v2_tl_qwt_s only; the other v2_* documents belong to other designs.
Build log matches the schematic (TL1 70.7107 Ohm, 90 Deg, 2 GHz; P1 50; P2 100).
Values: Z0=sqrt(5000) is theory-exact, not a standard value, as intended. Dossier complete.
SHOULD/NICE:
- theory.md says EL in radians, but the schematic stores 90 Deg. The deviation is already in build_log.md. Fix theory.md wording.
- spec.md says the -20 dB bandwidth is 36.7%. No goal checks it (only the band edges).
- Add a playbook line: "TLIN EL: send '90' in display degrees, not radians."
