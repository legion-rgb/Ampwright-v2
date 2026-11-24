# ne3508_bias: NE3508M04 DC bias at 20 mA, 3 V

Task: bias the Renesas NE3508M04 HJ-FET at Id = 20 mA with Vds = 3 V (source grounded). Theory picks Vgs.

Device: AWR's Renesas library netlist, imported with `import_netlist` and placed as a subcircuit (done by hand on 20 Nov; see README "Device demo").
Circuit: DC voltage source on the gate (Vgs from theory), swept DC source on the drain, source to ground. Watch the pin order (playbook).
Measurement: an I-V curve of Id vs Vds at the chosen Vgs, Vds swept 0 to 4 V, simulator as needed for the model (e.g. `aplac_dc`).
Documents: schematic `v2_ne3508_bias`, graph `v2_ne3508_bias_iv`.

Approved by the user: 21 Nov 2026, as written.
