# Report: rlc_notch (eval task, 21 Nov 2026)

Spec: a series L-C-R branch to ground between two 50 Ohm ports, with L = 100 nH, C = 0.1 pF and R = 1 Ohm (spec.md, approved as an eval task).
Build: L1 100 nH, C1 0.1 pF and R1 1 Ohm via add_shunt to GND, plus R2 1e-6 Ohm in series before P2. Sweep 1 to 2.2 GHz in 0.1 MHz steps (12001 points).

| goal | spec | theory | measured | result |
|---|---|---|---|---|
| s21_f0, 1591.55 MHz | -28.30 +/- 0.3 | -28.30 | -28.282 | PASS |
| s21_pass, 1 GHz | >= -0.5 | -0.0031 | -0.0032 | PASS |

Rounds: PASS in round 0, with no fix. The first Evaluator run missed s21_f0, because check_spec read only the first 2000 points (the graph_data default). The lead fixed check_spec (max_points 1e6, and a truncated trace now fails loudly), added a test, and re-ran it. Review: no MUST findings, and the tidy check is ok.

Open points:
- R2 (1e-6 Ohm) is needed because AWR rejects directly connected ports. A playbook line was added.
- 12001 points is heavy for one notch. A finer step only near f0 would be lighter, but it isn't needed.
