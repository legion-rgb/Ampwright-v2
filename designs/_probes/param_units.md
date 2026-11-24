# param_units probe (schematic v2_probe_units)

Caveat: my tool-call interface sent bare 1000 and 477.5 and 10 as JSON NUMBERS, not strings. Quoting them ("1000") sent literal quote characters. So true-string results exist only for 2*500, 1e-9, 1000 pF and the add_element "1000".

| Step | Sent | set_parameter new / unit | get_parameters value |
|---|---|---|---|
| 1 add C1 | number 1e-12 | n/a | 1 pF (number = SI, F) |
| 2a | 1000 (arrived as number) | 1e+15 / pF | 1e+15 pF (= 1000 F, SI) |
| 2a' | literal text "1000" with quotes | "1000" with quotes / pF | same, literal quotes stored (bad) |
| 2b | 2*500 (string) | 2*500 / pF | 2*500 pF (expression, display unit) |
| 2c | 1000 pF (string) | 1000 pF / pF | 1000 pF |
| 2d | 477.5 (arrived as number) | 477500000000000 / pF | 4.775e14 pF (SI) |
| 2e | 1e-9 (string) | 1e-9 / pF | 1e-9 pF (display unit, NOT SI) |
| 3 add L1 | number 1e-9 | n/a | 1 nH |
| 3 set L1 | 10 (arrived as number) | 10000000000 / nH | 1e10 nH (= 10 H, SI) |
| 4 add C2 | string "1000" | n/a | 1000 pF (display unit) |

Conclusion: JSON numbers are SI base units; real strings are read as display units (pF/nH).

## Follow-up (21 Nov, rc_lpf_fault seed)
- A string with a unit suffix ("4775 pF") is stored, but the simulator fails: "Error evaluating parameter C (Parse Error: syntax pF)". Row 2c above was never simulated.
- The text "4.775e-9" was stored as 4.775e-9 pF, which matches 2e.
- Rule: pass SI numbers. Use strings only for expressions or variable names.
- 3rd try: set_parameter with 4.775e-9 meant as a number was stored as the text "4.775e-9" pF. The value arrived as a string, because server _set_param uses ValueAsDouble only for a real float. 4th try: the expression "4.775*1000".
- Server fix (21 Nov, user yes): schematic._set_param now treats any plain-number string as SI (not ID). tests/test_params.py. Live after an MCP server restart.
