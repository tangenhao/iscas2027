# Hardware comparison data

The A100 numbers are measured STDiT-backbone results. Q-DARE uses
the optimized cycle-level schedule selected for the paper.

## Latency and video throughput

| Frames | A100 latency | Q-DARE latency | ViDA latency (derived) | Q-DARE/A100 | Q-DARE/ViDA |
|---:|---:|---:|---:|---:|---:|
| 64 | 46.648 s | 2.948 s | 2.968 s | 15.83x | 1.007x |
| 256 | 206.842 s | 11.853 s | 12.698 s | 17.45x | 1.071x |
| 512 | 445.607 s | 23.749 s | 25.914 s | 18.76x | 1.091x |
| Geomean | -- | -- | -- | 17.30x | 1.06x |

## A100 figure data

| Frames | A100 steps/s | Q-DARE steps/s | A100 steps/s/kW | Q-DARE steps/s/kW | Throughput gain | Energy-efficiency gain |
|---:|---:|---:|---:|---:|---:|---:|
| 64 | 0.643 | 6.446 | 1.677 | 613.443 | 10.02x | 365.8x |
| 256 | 0.145 | 1.603 | 0.405 | 152.558 | 11.05x | 376.8x |
| 512 | 0.067 | 0.800 | 0.200 | 76.139 | 11.88x | 381.6x |
| Geomean | 0.184 | 2.022 | 0.514 | 192.430 | 10.96x | 374.7x |

## ViDA-normalized results

| Metric | Q-DARE/ViDA |
|---|---:|
| 64F video throughput | 1.007x |
| 256F video throughput | 1.071x |
| 512F video throughput | 1.091x |
| Video-throughput geomean | 1.06x |
| Area-efficiency geomean | 24.07x |

The ViDA ratios use its reported A100-relative results. The
Q-DARE/ViDA ratios divide the corresponding A100-relative metrics.

## Area-efficiency calculation

For each workload, Q-DARE/A100 area efficiency is computed as

`(Q-DARE video throughput / A100 video throughput) * (826 / 32.294)`,

where 826 mm^2 is the A100 die area and 32.294 mm^2 is the complete
technology-normalized Q-DARE configuration area. This gives 404.77x,
446.36x, and 479.92x for 64, 256, and 512 frames, respectively, with a
442.61x geomean. ViDA reports only an 18.39x geomean area-efficiency
ratio; therefore Q-DARE/ViDA area efficiency is `442.61 / 18.39 = 24.07x`.
Per-workload ViDA area-efficiency values are not reported.

## PPA

| Quantity | Value |
|---|---:|
| Q-DARE per-core 7nm area | 0.134 mm^2 |
| Q-DARE per-core 7nm power | 43.6 mW |
| Complete-configuration 7nm area | 32.294 mm^2 |
| Complete-configuration 7nm power | 10.508 W |
| A100 die area | 826.0 mm^2 |
| ViDA 7nm area | 2.03 mm^2 |

PPA is technology-normalized from the available 28nm results.
NoC, clock tree, I/O, shared memory, and DRAM overhead are not included;
the mapped source netlist also omits the complete PEA datapath.

Run `python3 scripts/build_hardware_comparison.py` from the repository root.
