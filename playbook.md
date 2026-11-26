# Playbook: lessons learned

Every agent reads this before working. Add one line per new lesson, with the date and the design it came from. Keep it short; delete lessons that stop being true.

## Units and parameters
- Numbers are SI (Ohm, F, H, m, Hz) and angles are **radians**: 90 deg electrical length is `1.5707963`.
- Part values: a plain number is **SI** (`{'C': 4.77e-10}` reads back `477` pF). Other strings are expressions or `add_equation` variables read in display units (`'Cval'`, `'4.775*100'` = 477.5 pF). Since the server fix of 21 Nov, plain numbers sent as text are SI too (`'4.775e-9'` = 4.775 nF). Before that fix (and until the MCP server restarts) text such as `'4.775e-9'` was read in pF and `'4775'` in pF, so don't send display-unit numbers as text. A unit suffix (`'4775 pF'`) is stored but **fails to simulate**. Don't wrap values in extra quotes (stored literally). Always confirm with `get_parameters` before simulating (`designs/_probes/param_units.md`).
- Check every model name with `search_models` first. The first call reads the whole library (about 15 s).

## Schematics
- `helpers.route` only prevents electrical shorts; it does not avoid visual crossings or wires over bodies. Check `list_wires` after wiring and fix placement by hand (rule in `../CLAUDE.md`).
- A 2-pin part at rotation 0 runs left to right (pin 1 left); at 270 it runs top to bottom (pin 1 on top). Use 270 for shunt parts, or `add_shunt`.
- `set_frequencies(document=...)` gives one document its own sweep; without `document` it changes the project sweep for everything. The guard hook denies `set_frequencies` and `add_equation` without `document` (21 Nov): always pass `document='v2_<slug>'`.
- `graph_data` reads the real part only.
- If `v2_<slug>` or its graph already exists before the build, say so in `build_log.md` and rebuild in place, so the dossier explains it; cause seen: an earlier Ampwright (then Fieldnote) Quick-mode turn built it without subagents or a dossier (26 Nov, fn_rc_check).

## Simulation
- A COM call can't be interrupted. Tool calls time out after 15 min, but AWR keeps working and later calls queue. Use `simulate` then `wait_for_simulation` for long runs.
- An AWR modal dialog blocks every COM call. If calls time out, check AWR for an open dialog and ask the user.

## EM (AXIEM / Analyst)
- Set the stackup before shapes and ports. At most 3 dielectric layers. Shapes can't be deleted via COM: delete the EM structure and rebuild.
- A default wave port must sit exactly on the boundary. A differential lumped port needs its `-` terminal on the facing edge. Lumped Down needs ground under it. Run `check_em_setup` before every EM simulation.
- Analyst needs a real boundary object, not a polygon on EMBoundary.
- AXIEM S-parameters stay 50 Ohm referenced whatever the port impedance.
- Theory offsets seen: T-junction stubs +2.7% (junction not modelled); patch edge resistance from Balanis (160 Ohm) disagrees with AXIEM (352 Ohm). Check before using inset-feed depths.

## Validated references
- `tests/validate.py` (71 schematic checks) and `tests/validate_em.py` (21 EM checks) pass against `tests/rf_theory.py`. Reuse their circuits and tolerances as patterns.

## DC / device models
- EEHEMT near pinch-off has strongly Vds-dependent Id (Gamma, Kapa), so don't assume flat saturation when picking Vgs; search Vgs at the target Vds (21 Nov, ne3508_bias).
- TLIN EL (tl_qwt, 21 Nov): send radians as a number (`1.5707963` = 90 deg). The text '90' gave 90 Deg on the old server, but after the server fix plain-number text is SI, so '90' would be 90 rad. Confirm EL reads back 90 Deg.
- Shunt-only circuits (rlc_notch, 21 Nov): AWR rejects two ports on one node ("Ports may not be connected together"). Plan a tiny series part, such as RES 1e-6 Ohm, between them from the start.
- Long sweeps (rlc_notch, 21 Nov): `graph_data` returns at most `max_points` (2000 by default). For more points, pass `max_points`. check_spec now asks for 1e6 points and fails a truncated trace.
- Optimizer (E.1, 21 Nov): `add_opt_goal` per goal, `set_opt_variable` with SI bounds, then `run_optimizer`. A goal cost comes from the last simulation, so simulate first. Simplex is fast for 1-3 lumped variables: 477 pF from 1 nF in 0.7 s. Clear the flags and goals afterwards, or the next `run_optimizer` on another schematic refuses.
- Vendor library (E.5, 21 Nov): `C:\Program Files (x86)\AWR\AWRDE\17\Library` is read only; never write there. It holds about 2528 Renesas Touchstone files (`RENESAS_DEVICES/Data/**/*.s2p`) and 7 netlists (`RENESAS_DEVICES/Nonlinear`). Find parts with Glob, for example `**/*NE3508*`. Bring in a `.net` with `import_netlist` (read the file, pass its text), as ne3508_bias did. There is no Touchstone import tool yet, so ask the lead before planning around an `.s2p`.
