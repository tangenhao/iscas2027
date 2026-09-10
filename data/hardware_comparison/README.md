# Hardware comparison data

This directory combines measured A100 data, Q-DARE cycle projections,
the requested 28-to-7-nm linear PPA scaling, and ViDA Figure 7 data.

## Main comparison

| Frames | A100 measured latency | ViDA/A100 digitized | ViDA bridged latency | Q-DARE ideal-fused latency | Q-DARE/A100 | Q-DARE/ViDA | Upper-bound Q-DARE/A100 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 64 | 46.648 s | 15.72x | 2.968 s | 2.948 s | 15.83x | 1.01x | 17.09x |
| 256 | 206.842 s | 16.29x | 12.698 s | 11.853 s | 17.45x | 1.07x | 18.88x |
| 512 | 445.607 s | 17.20x | 25.914 s | 23.749 s | 18.76x | 1.09x | 20.39x |

## PPA scaling

| Quantity | Single core | 241-core equal-peak system |
|---|---:|---:|
| 7-nm normalized area | 0.134 mm^2 | 32.294 mm^2 |
| 7-nm normalized power | 43.6 mW | 10.508 W |
| INT8 MACs | 1,296 | 312,336 |
| FP16 MACs | 36 | 8,676 |
| SRAM | 238.5 KiB | 56.13 MiB |

These system values are direct linear scaling as requested. They do not add
NoC, clock-tree, I/O, shared-memory, or off-chip-memory overhead.

## Reproduction and limits

Run `python3 scripts/build_hardware_comparison.py` from the repository root.
ViDA's Figure 7 uses a log4 y-axis. The Open-Sora GPU-bar geometry gives
15.718x, 16.289x, and 17.195x for 64/256/512 frames at 512 resolution;
the vector-derived eight-workload geomean is 16.438x, reproducing the paper's
printed 16.44x geomean.

- A100 latency is measured FP16 STDiT-only latency; A100 power is averaged over the measured-video pipeline window.
- Q-DARE latency is a 241-core, 1GHz, 19-step cycle-model projection.
- Q-DARE 7nm area and power use the user-specified per-core linear scale of 0.134 mm2 and 43.6 mW.
- The available 28nm synthesis/power netlist omitted the PEA datapath, so Q-DARE power and area remain optimistic estimates.
- ViDA per-workload speedups are digitized from Figure 7 and bridged through this work's measured A100 latency; they are not direct same-run ViDA measurements.
