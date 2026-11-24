# review: rc_lpf_fault
MUST: none.
Tidiness: check_tidy ok. 4 wires, no crossings, none over bodies or pins; R1 horizontal, C1 vertical shunt, GND below. Clean.
Build log vs schematic: matches part for part (R1 50, C1 4.775*100 pF, P1, P2, GND, wire coordinates).
Naming: only v2_rc_lpf_fault and v2_rc_lpf_fault_s belong to this design; other v2_* documents belong to other designs. No stray graphs or schematics.
Values: 50 Ohm / 477.5 pF per theory; ideal, no line widths.
SHOULD / NICE:
- NICE: sweep starts at 100 kHz, spec.md says 10 kHz. Deviation is documented in build_log and verdict; harmless.
- NICE: 477.5 pF is not a standard value; theory.md notes 470 pF (E12) would give about -6.4 dB. Acceptable for an ideal-model test.
- NICE: report.md not yet written (lead's step).
- NICE: spec.md and build_log say "477 pF" in places and "477.5" in others; unify.
Playbook: no new line (the 4.775*1000 slip is already covered by the units lesson).
