# ne3508_bias theory

Topology: single HJ-FET, source grounded, DC Vgs source on gate, swept DC Vds source on drain. Rejected: self-bias (Rs) and resistive divider/choke networks; the spec asks only for fixed Vgs and Vds, and extra parts add IR drops.

Netlist (read-only): C:\Program Files (x86)\AWR\AWRDE\17\Library\RENESAS_DEVICES\Nonlinear\Discrete\5_LowNoise_GaAsFET_HBT_HJ_FET\NE3508M04_v124.net
Subcircuit NE3508M04_v124, pin order (PORT P=): P1 = gate (node 4), P2 = drain (node 5), P3 = source (node 3). Verify in the placed subckt, per the playbook.

Core model: EEHEMT (Vto=-0.508, Gamma=0.01979, Vgo=-0.06959, Vch=1.475, Gmmax=0.4175, Vsat=0.7125, Kapa=0.1232, Peff=25.24, Lambda=0.03, Rd=1.259, Rs=0.938, Rg=0.982), plus parasitic C/L (no DC effect; Rd/Rs/Rg are series DC drops).

Vgs: I did not compute it from the EEHEMT equations. Ipk0 = Gmmax*Vch/Peff = 24 mA suggests Vgs near -0.1 V, but that is only a rough guess. Calibration: Id = 20.36 mA at Vgs=0, Vds=0.1 V (README).
Search plan: DC sweep Vgs from -0.5 to 0 V in 0.05 V steps at Vds=3 V, read Id, then secant or bisect to Id = 20.00 mA within 0.1 mA. Round Vgs to 1 mV. Then sweep Vds 0..4 V at that Vgs.

Models expected: the netlist subckt (imported), DC voltage sources (two, one swept), GND. No MSUB/MLIN.
Assumptions: DC sim (e.g. aplac_dc) handles EEHEMT. The cap and inductor parasitics are open or short at DC, so Id is flat in Vds above about 1.5 V apart from Lambda=0.03 (about 3% per V).

> **Superseded (lead, 21 Nov):** the flat-Id assumption and the Vgs near -0.1 V guess were wrong. Near pinch-off this EEHEMT has strongly Vds-dependent Id; the Vgs search in build_log.md found -0.314 V. See verdict.md.
