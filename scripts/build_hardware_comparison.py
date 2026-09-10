#!/usr/bin/env python3
"""Build the paper's A100/ViDA/Q-DARE comparison artifacts.

The script deliberately separates measurements, model projections, and
technology-scaled estimates.  ViDA's per-workload A100 speedups are digitized
from the vector geometry of Figure 7 in the ASP-DAC 2025 paper; the paper only
prints the 16.44x geomean as text.
"""

import csv
import json
import math
from functools import reduce
from operator import mul
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCELERATOR_RESULTS = (
    ROOT.parent
    / "llama_fpga_test"
    / "sim"
    / "cycle_model"
    / "results"
    / "a100_measured_comparison"
    / "a100_comparison.json"
)
OUTPUT_DIR = ROOT / "data" / "hardware_comparison"
TEX_OUTPUT = ROOT / "tex" / "generated" / "hardware_results.tex"

CORE_COUNT = 241
FREQUENCY_GHZ = 1.0
INT8_MACS_PER_CORE = 1296
FP16_MACS_PER_CORE = 36
SRAM_KIB_PER_CORE = 238.5
AREA_28NM_MM2_PER_CORE = 4.2624
POWER_28NM_W_PER_CORE = 0.116372
AREA_SCALE_28_TO_7 = 31.818
POWER_SCALE_28_TO_7 = 2.667
AREA_7NM_MM2_PER_CORE = 0.134
POWER_7NM_W_PER_CORE = 0.0436
VIDA_AREA_7NM_MM2 = 2.03
VIDA_FP16_MACS = 640

# Figure 7 vector coordinates for the three blue GPU bars (OS 64/256/512-512).
# The y axis is log4: baseline=1 and adjacent major ticks differ by 4x.
VIDA_FIG7_BASE_Y = 521.925
VIDA_FIG7_MAJOR_TICK_PT = (270.073 - 236.824) / 3.0
VIDA_FIG7_ALL_GPU_BAR_TOP_Y = (
    543.949, 544.234, 544.667, 543.660, 544.234, 544.523, 544.523, 544.667
)
VIDA_FIG7_OS_GPU_BAR_TOP_Y = VIDA_FIG7_ALL_GPU_BAR_TOP_Y[:3]


def geomean(values):
    return reduce(mul, values, 1.0) ** (1.0 / len(values))


def vida_speedups_from_figure7():
    return [
        4.0 ** ((y - VIDA_FIG7_BASE_Y) / VIDA_FIG7_MAJOR_TICK_PT)
        for y in VIDA_FIG7_OS_GPU_BAR_TOP_Y
    ]


def vida_all_workload_geomean_from_figure7():
    values = [
        4.0 ** ((y - VIDA_FIG7_BASE_Y) / VIDA_FIG7_MAJOR_TICK_PT)
        for y in VIDA_FIG7_ALL_GPU_BAR_TOP_Y
    ]
    return geomean(values)


def load_rows():
    with ACCELERATOR_RESULTS.open(encoding="utf-8") as stream:
        accelerator_rows = json.load(stream)

    vida_speedups = vida_speedups_from_figure7()
    rows = []
    for source, vida_speedup in zip(accelerator_rows, vida_speedups):
        a100_latency = source["a100_latency_s"]
        a100_power = source["a100_average_power_w"]
        fused_latency = source["ideal_fused_latency_s"]
        upper_latency = source["ideal_overlap_latency_s"]
        vida_latency = a100_latency / vida_speedup
        system_area = AREA_7NM_MM2_PER_CORE * CORE_COUNT
        system_power = POWER_7NM_W_PER_CORE * CORE_COUNT

        rows.append({
            "frames": source["frames"],
            "resolution": source["resolution"],
            "latent_t": source["stdit_t"],
            "a100_latency_s_measured": a100_latency,
            "a100_power_w_measured_pipeline_window": a100_power,
            "a100_throughput_video_per_s": 1.0 / a100_latency,
            "vida_a100_speedup_digitized": vida_speedup,
            "vida_latency_s_bridged": vida_latency,
            "vida_throughput_video_per_s_bridged": 1.0 / vida_latency,
            "qdare_fused_latency_s_projected": fused_latency,
            "qdare_fused_a100_speedup": source["ideal_fused_system_speedup"],
            "qdare_fused_vida_speedup_bridged": vida_latency / fused_latency,
            "qdare_upper_latency_s_projected": upper_latency,
            "qdare_upper_a100_speedup": source["ideal_overlap_system_speedup"],
            "qdare_upper_vida_speedup_bridged": vida_latency / upper_latency,
            "qdare_system_area_7nm_mm2_scaled": system_area,
            "qdare_system_power_7nm_w_scaled": system_power,
            "qdare_fused_energy_j_proxy": fused_latency * system_power,
            "qdare_upper_energy_j_proxy": upper_latency * system_power,
            "a100_energy_j_proxy": a100_latency * a100_power,
            "qdare_fused_energy_efficiency_vs_a100_proxy": (
                a100_latency * a100_power / (fused_latency * system_power)
            ),
            "qdare_upper_energy_efficiency_vs_a100_proxy": (
                a100_latency * a100_power / (upper_latency * system_power)
            ),
            "qdare_fused_area_eff_video_per_s_per_mm2": (
                1.0 / fused_latency / system_area
            ),
            "vida_area_eff_video_per_s_per_mm2_bridged": (
                1.0 / vida_latency / VIDA_AREA_7NM_MM2
            ),
        })
    return rows


def summary(rows):
    return {
        "comparison_scope": "STDiT backbone per generated video",
        "qdare_steps": 19,
        "a100_steps": 30,
        "frequency_ghz": FREQUENCY_GHZ,
        "qdare_equal_peak_core_count": CORE_COUNT,
        "qdare_nominal_int8_tops": (
            CORE_COUNT * INT8_MACS_PER_CORE * 2.0 * FREQUENCY_GHZ / 1000.0
        ),
        "qdare_single_core": {
            "int8_macs": INT8_MACS_PER_CORE,
            "fp16_macs": FP16_MACS_PER_CORE,
            "sram_kib": SRAM_KIB_PER_CORE,
            "area_28nm_mm2": AREA_28NM_MM2_PER_CORE,
            "power_28nm_w": POWER_28NM_W_PER_CORE,
            "area_scale_28nm_to_7nm": AREA_SCALE_28_TO_7,
            "power_scale_28nm_to_7nm": POWER_SCALE_28_TO_7,
            "area_7nm_mm2": AREA_7NM_MM2_PER_CORE,
            "power_7nm_w": POWER_7NM_W_PER_CORE,
        },
        "qdare_241_core_linear_scale": {
            "int8_macs": CORE_COUNT * INT8_MACS_PER_CORE,
            "fp16_macs": CORE_COUNT * FP16_MACS_PER_CORE,
            "sram_kib": CORE_COUNT * SRAM_KIB_PER_CORE,
            "area_7nm_mm2": CORE_COUNT * AREA_7NM_MM2_PER_CORE,
            "power_7nm_w": CORE_COUNT * POWER_7NM_W_PER_CORE,
        },
        "vida": {
            "technology": "32nm normalized to 7nm",
            "frequency_ghz": 1.0,
            "fp16_macs": VIDA_FP16_MACS,
            "area_7nm_mm2": VIDA_AREA_7NM_MM2,
            "power": "not reported",
            "reported_a100_speedup_geomean": 16.44,
            "reported_a100_area_efficiency_geomean": 18.39,
            "digitized_all_workload_a100_speedup_geomean": (
                vida_all_workload_geomean_from_figure7()
            ),
            "digitized_open_sora_a100_speedups": [
                row["vida_a100_speedup_digitized"] for row in rows
            ],
        },
        "geomeans": {
            "qdare_fused_vs_a100": geomean(
                [row["qdare_fused_a100_speedup"] for row in rows]
            ),
            "qdare_upper_vs_a100": geomean(
                [row["qdare_upper_a100_speedup"] for row in rows]
            ),
            "qdare_fused_vs_vida_bridged": geomean(
                [row["qdare_fused_vida_speedup_bridged"] for row in rows]
            ),
            "qdare_upper_vs_vida_bridged": geomean(
                [row["qdare_upper_vida_speedup_bridged"] for row in rows]
            ),
            "qdare_fused_energy_efficiency_vs_a100_proxy": geomean(
                [row["qdare_fused_energy_efficiency_vs_a100_proxy"] for row in rows]
            ),
            "qdare_upper_energy_efficiency_vs_a100_proxy": geomean(
                [row["qdare_upper_energy_efficiency_vs_a100_proxy"] for row in rows]
            ),
        },
        "method_notes": [
            "A100 latency is measured FP16 STDiT-only latency; A100 power is averaged over the measured-video pipeline window.",
            "Q-DARE latency is a 241-core, 1GHz, 19-step cycle-model projection.",
            "Q-DARE 7nm area and power use the user-specified per-core linear scale of 0.134 mm2 and 43.6 mW.",
            "The available 28nm synthesis/power netlist omitted the PEA datapath, so Q-DARE power and area remain optimistic estimates.",
            "ViDA per-workload speedups are digitized from Figure 7 and bridged through this work's measured A100 latency; they are not direct same-run ViDA measurements.",
        ],
    }


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_tex(path, rows, data):
    gm = data["geomeans"]
    first = rows[0]
    core_throughput_64 = (
        1.0 / first["qdare_fused_latency_s_projected"] / CORE_COUNT
    )
    lines = [
        "% Generated by scripts/build_hardware_comparison.py; do not edit.",
        "\\newcommand{\\QDARECoreAreaSeven}{0.134}",
        "\\newcommand{\\QDARECorePowerSevenMW}{43.6}",
        "\\newcommand{\\QDARESystemCores}{241}",
        "\\newcommand{\\QDARESystemAreaSeven}{32.294}",
        "\\newcommand{\\QDARESystemPowerSeven}{10.508}",
        "\\newcommand{\\QDARESystemINTMACs}{312336}",
        "\\newcommand{\\QDARESystemFPMACs}{8676}",
        "\\newcommand{\\QDARESystemSRAMMiB}{56.13}",
        "\\newcommand{\\QDARECoreThroughputSF}{%.5f}" % core_throughput_64,
        "\\newcommand{\\QDARESystemThroughputSF}{%.3f}"
        % (1.0 / first["qdare_fused_latency_s_projected"]),
        "\\newcommand{\\ViDABridgedThroughputSF}{%.3f}"
        % first["vida_throughput_video_per_s_bridged"],
        "\\newcommand{\\QDAREAreaEfficiencySF}{%.4f}"
        % first["qdare_fused_area_eff_video_per_s_per_mm2"],
        "\\newcommand{\\ViDAAreaEfficiencySF}{%.4f}"
        % first["vida_area_eff_video_per_s_per_mm2_bridged"],
        "\\newcommand{\\QDAREFusedGeoA}{%.2f}" % gm["qdare_fused_vs_a100"],
        "\\newcommand{\\QDAREUpperGeoA}{%.2f}" % gm["qdare_upper_vs_a100"],
        "\\newcommand{\\QDAREFusedGeoViDA}{%.2f}" % gm["qdare_fused_vs_vida_bridged"],
        "\\newcommand{\\QDAREUpperGeoViDA}{%.2f}" % gm["qdare_upper_vs_vida_bridged"],
        "\\newcommand{\\QDAREFusedGeoEnergyA}{%.1f}" % gm["qdare_fused_energy_efficiency_vs_a100_proxy"],
        "\\newcommand{\\QDAREUpperGeoEnergyA}{%.1f}" % gm["qdare_upper_energy_efficiency_vs_a100_proxy"],
        "\\newcommand{\\LatencyComparisonRows}{%",
    ]
    for index, row in enumerate(rows):
        suffix = " \\\\"
        lines.append(
            "  %d & %.3f & %.2f$\\times$ & %.3f & %.3f & %.2f$\\times$ & %.2f$\\times$%s"
            % (
                row["frames"],
                row["a100_latency_s_measured"],
                row["vida_a100_speedup_digitized"],
                row["vida_latency_s_bridged"],
                row["qdare_fused_latency_s_projected"],
                row["qdare_fused_a100_speedup"],
                row["qdare_fused_vida_speedup_bridged"],
                suffix,
            )
        )
    lines.extend(["}", "\\newcommand{\\UpperBoundRows}{%"])
    for index, row in enumerate(rows):
        suffix = " \\\\"
        lines.append(
            "  %d & %.3f & %.2f$\\times$ & %.2f$\\times$ & %.1f$\\times$%s"
            % (
                row["frames"],
                row["qdare_upper_latency_s_projected"],
                row["qdare_upper_a100_speedup"],
                row["qdare_upper_vida_speedup_bridged"],
                row["qdare_upper_energy_efficiency_vs_a100_proxy"],
                suffix,
            )
        )
    lines.extend(["}", "\\newcommand{\\EnergyComparisonRows}{%"])
    for row in rows:
        lines.append(
            "  %d & %.2f & %.3f & %.1f$\\times$ & %.1f$\\times$ \\\\"
            % (
                row["frames"],
                row["a100_power_w_measured_pipeline_window"],
                row["qdare_system_power_7nm_w_scaled"],
                row["qdare_fused_energy_efficiency_vs_a100_proxy"],
                row["qdare_upper_energy_efficiency_vs_a100_proxy"],
            )
        )
    lines.extend(["}", "\\newcommand{\\FullComparisonRows}{%"])
    for row in rows:
        lines.append(
            "  %d & %.3f & %.2f & %.2f$\\times$ & %.3f & "
            "%.3f & %.2f$\\times$ & %.2f$\\times$ & %.1f$\\times$ & "
            "%.3f & %.2f$\\times$ & %.2f$\\times$ & %.1f$\\times$ \\\\"
            % (
                row["frames"],
                row["a100_latency_s_measured"],
                row["a100_power_w_measured_pipeline_window"],
                row["vida_a100_speedup_digitized"],
                row["vida_latency_s_bridged"],
                row["qdare_fused_latency_s_projected"],
                row["qdare_fused_a100_speedup"],
                row["qdare_fused_vida_speedup_bridged"],
                row["qdare_fused_energy_efficiency_vs_a100_proxy"],
                row["qdare_upper_latency_s_projected"],
                row["qdare_upper_a100_speedup"],
                row["qdare_upper_vida_speedup_bridged"],
                row["qdare_upper_energy_efficiency_vs_a100_proxy"],
            )
        )
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(path, rows, data):
    lines = [
        "# Hardware comparison data",
        "",
        "This directory combines measured A100 data, Q-DARE cycle projections,",
        "the requested 28-to-7-nm linear PPA scaling, and ViDA Figure 7 data.",
        "",
        "## Main comparison",
        "",
        "| Frames | A100 measured latency | ViDA/A100 digitized | ViDA bridged latency | Q-DARE ideal-fused latency | Q-DARE/A100 | Q-DARE/ViDA | Upper-bound Q-DARE/A100 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {frames} | {a100_latency_s_measured:.3f} s | "
            "{vida_a100_speedup_digitized:.2f}x | {vida_latency_s_bridged:.3f} s | "
            "{qdare_fused_latency_s_projected:.3f} s | "
            "{qdare_fused_a100_speedup:.2f}x | "
            "{qdare_fused_vida_speedup_bridged:.2f}x | "
            "{qdare_upper_a100_speedup:.2f}x |".format(**row)
        )
    lines.extend([
        "",
        "## PPA scaling",
        "",
        "| Quantity | Single core | 241-core equal-peak system |",
        "|---|---:|---:|",
        "| 7-nm normalized area | 0.134 mm^2 | 32.294 mm^2 |",
        "| 7-nm normalized power | 43.6 mW | 10.508 W |",
        "| INT8 MACs | 1,296 | 312,336 |",
        "| FP16 MACs | 36 | 8,676 |",
        "| SRAM | 238.5 KiB | 56.13 MiB |",
        "",
        "These system values are direct linear scaling as requested. They do not add",
        "NoC, clock-tree, I/O, shared-memory, or off-chip-memory overhead.",
        "",
        "## Reproduction and limits",
        "",
        "Run `python3 scripts/build_hardware_comparison.py` from the repository root.",
        "ViDA's Figure 7 uses a log4 y-axis. The Open-Sora GPU-bar geometry gives",
        "15.718x, 16.289x, and 17.195x for 64/256/512 frames at 512 resolution;",
        "the vector-derived eight-workload geomean is 16.438x, reproducing the paper's",
        "printed 16.44x geomean.",
        "",
    ])
    lines.extend(["- " + note for note in data["method_notes"]])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = load_rows()
    data = summary(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "hardware_comparison.csv", rows)
    (OUTPUT_DIR / "hardware_comparison.json").write_text(
        json.dumps({"summary": data, "workloads": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_readme(OUTPUT_DIR / "README.md", rows, data)
    write_tex(TEX_OUTPUT, rows, data)
    print("wrote %s" % OUTPUT_DIR)
    print("wrote %s" % TEX_OUTPUT)


if __name__ == "__main__":
    main()
