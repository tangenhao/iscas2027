#!/usr/bin/env python3
"""Build the paper's consistent A100, ViDA, and Q-DARE result files."""

import csv
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LLAMA_ROOT = ROOT.parent / "llama_fpga_test"
A100_ROOT = ROOT / "data"
COMPARISON_SOURCE = (
    LLAMA_ROOT / "sim" / "cycle_model" / "results" /
    "a100_measured_comparison" / "a100_comparison.json"
)
OUTPUT_DIR = ROOT / "data" / "hardware_comparison"
TEX_OUTPUT = ROOT / "tex" / "generated" / "hardware_results.tex"

FRAMES = (64, 256, 512)
QDARE_STEPS = 19
A100_STEPS = 30
FREQUENCY_GHZ = 1.0

# Technology-normalized complete-configuration PPA used for the GPU plots.
QDARE_AREA_7NM_MM2 = 32.294
QDARE_POWER_7NM_W = 10.5076
A100_AREA_MM2 = 826.0

# Per-core implementation entries used in Table II.
QDARE_CORE_AREA_7NM_MM2 = 0.134
QDARE_CORE_POWER_7NM_MW = 43.6
VIDA_AREA_7NM_MM2 = 2.03
VIDA_THROUGHPUT_VS_A100_GEOMEAN = 16.44
VIDA_AREA_EFFICIENCY_VS_A100 = 18.39

# ViDA Figure 7 vector coordinates. Its y-axis is logarithmic base four.
VIDA_FIG7_BASE_Y = 521.925
VIDA_FIG7_MAJOR_TICK_PT = (270.073 - 236.824) / 3.0
VIDA_FIG7_GPU_TOP_Y = (543.949, 544.234, 544.667)


def geomean(values):
    return math.exp(sum(math.log(float(value)) for value in values) /
                    len(values))


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def vida_speedups_from_figure7():
    return [
        4.0 ** ((y - VIDA_FIG7_BASE_Y) / VIDA_FIG7_MAJOR_TICK_PT)
        for y in VIDA_FIG7_GPU_TOP_Y
    ]


def load_rows():
    schedule_by_frames = {
        int(row["frames"]): row for row in load_json(COMPARISON_SOURCE)
    }
    rows = []

    for frames, vida_speedup in zip(FRAMES, vida_speedups_from_figure7()):
        measured = load_json(
            A100_ROOT / ("os_%d_512_fp" % frames) / "combined_summary.json"
        )
        schedule = schedule_by_frames[frames]
        a100_latency = float(
            measured["latency"]["average_stdit_backbone_seconds_per_video"]
        )
        a100_power = float(measured["power"]["average_gpu_power_w"])
        qdare_latency = float(schedule["ideal_fused_latency_s"])
        vida_latency = a100_latency / vida_speedup

        a100_video_rate = 1.0 / a100_latency
        qdare_video_rate = 1.0 / qdare_latency
        vida_video_rate = 1.0 / vida_latency
        a100_step_rate = A100_STEPS / a100_latency
        qdare_step_rate = QDARE_STEPS / qdare_latency
        a100_step_eff = a100_step_rate / a100_power
        qdare_step_eff = qdare_step_rate / QDARE_POWER_7NM_W
        qdare_vs_a100_area_eff = (
            (qdare_video_rate / QDARE_AREA_7NM_MM2) /
            (a100_video_rate / A100_AREA_MM2)
        )

        rows.append({
            "frames": frames,
            "resolution": 512,
            "stdit_t": int(schedule["stdit_t"]),
            "a100_latency_s": a100_latency,
            "a100_power_w": a100_power,
            "qdare_latency_s_cycle_model": qdare_latency,
            "vida_a100_speedup": vida_speedup,
            "vida_latency_s_derived": vida_latency,
            "a100_video_per_s": a100_video_rate,
            "qdare_video_per_s": qdare_video_rate,
            "vida_video_per_s_derived": vida_video_rate,
            "a100_steps_per_s": a100_step_rate,
            "qdare_steps_per_s": qdare_step_rate,
            "a100_steps_per_s_per_w": a100_step_eff,
            "qdare_steps_per_s_per_w": qdare_step_eff,
            "a100_steps_per_s_per_kw": a100_step_eff * 1000.0,
            "qdare_steps_per_s_per_kw": qdare_step_eff * 1000.0,
            "qdare_vs_a100_video_throughput": a100_latency / qdare_latency,
            "qdare_vs_a100_step_throughput": qdare_step_rate / a100_step_rate,
            "qdare_vs_a100_step_energy_efficiency": qdare_step_eff / a100_step_eff,
            "qdare_vs_vida_video_throughput": qdare_video_rate / vida_video_rate,
            "qdare_vs_a100_area_efficiency": qdare_vs_a100_area_eff,
            "a100_energy_j": a100_latency * a100_power,
            "qdare_energy_j": qdare_latency * QDARE_POWER_7NM_W,
        })

    return rows


def build_summary(rows):
    geomeans = {
        "vida_vs_a100_video_throughput": geomean(
            [row["vida_a100_speedup"] for row in rows]),
        "qdare_vs_a100_video_throughput": geomean(
            [row["qdare_vs_a100_video_throughput"] for row in rows]),
        "qdare_vs_a100_step_throughput": geomean(
            [row["qdare_vs_a100_step_throughput"] for row in rows]),
        "qdare_vs_a100_step_energy_efficiency": geomean(
            [row["qdare_vs_a100_step_energy_efficiency"] for row in rows]),
        "qdare_vs_vida_video_throughput": geomean(
            [row["qdare_vs_vida_video_throughput"] for row in rows]),
        "qdare_vs_a100_area_efficiency": geomean(
            [row["qdare_vs_a100_area_efficiency"] for row in rows]),
        "a100_steps_per_s": geomean(
            [row["a100_steps_per_s"] for row in rows]),
        "qdare_steps_per_s": geomean(
            [row["qdare_steps_per_s"] for row in rows]),
        "a100_steps_per_s_per_kw": geomean(
            [row["a100_steps_per_s_per_kw"] for row in rows]),
        "qdare_steps_per_s_per_kw": geomean(
            [row["qdare_steps_per_s_per_kw"] for row in rows]),
    }
    geomeans["qdare_vs_vida_area_efficiency"] = (
        geomeans["qdare_vs_a100_area_efficiency"] /
        VIDA_AREA_EFFICIENCY_VS_A100
    )

    return {
        "comparison_scope": "STDiT backbone per generated video",
        "qdare_steps": QDARE_STEPS,
        "a100_steps": A100_STEPS,
        "frequency_ghz": FREQUENCY_GHZ,
        "qdare_area_7nm_mm2": QDARE_AREA_7NM_MM2,
        "qdare_power_7nm_w": QDARE_POWER_7NM_W,
        "a100_die_area_mm2": A100_AREA_MM2,
        "qdare_core": {
            "area_7nm_mm2": QDARE_CORE_AREA_7NM_MM2,
            "power_7nm_mw": QDARE_CORE_POWER_7NM_MW,
            "int8_macs": 1296,
            "fp16_macs": 36,
            "sram_kib": 238.5,
        },
        "vida": {
            "area_7nm_mm2": VIDA_AREA_7NM_MM2,
            "reported_a100_speedup_geomean": VIDA_THROUGHPUT_VS_A100_GEOMEAN,
            "reported_a100_area_efficiency_geomean": VIDA_AREA_EFFICIENCY_VS_A100,
            "digitized_open_sora_a100_speedups": [
                row["vida_a100_speedup"] for row in rows
            ],
        },
        "geomeans": geomeans,
        "method_notes": [
            "A100 latency and power are measured FP16 STDiT-backbone results.",
            "Q-DARE latency uses the optimized cycle-level schedule stored in the cycle-model comparison source.",
            "The ViDA workload ratios are digitized from Figure 7; Q-DARE/ViDA divides both accelerators' A100-relative video-throughput ratios.",
            "Q-DARE PPA is technology-normalized from the available 28nm synthesis and power reports.",
            "The PPA values omit NoC, clock-tree, I/O, shared-memory, and DRAM overhead; the mapped source netlist also omits the complete PEA datapath.",
        ],
    }


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]),
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_tex(path, rows, data):
    gm = data["geomeans"]
    lines = [
        "% Generated by scripts/build_hardware_comparison.py; do not edit.",
        "\\newcommand{\\QDAREAreaSeven}{%.3f}" % QDARE_AREA_7NM_MM2,
        "\\newcommand{\\QDAREPowerSeven}{%.3f}" % QDARE_POWER_7NM_W,
        "\\newcommand{\\QDAREGeoA}{%.2f}" % gm["qdare_vs_a100_video_throughput"],
        "\\newcommand{\\QDAREStepGeoA}{%.2f}" % gm["qdare_vs_a100_step_throughput"],
        "\\newcommand{\\QDAREEnergyGeoA}{%.1f}" % gm["qdare_vs_a100_step_energy_efficiency"],
        "\\newcommand{\\QDAREViDAThroughputGeo}{%.2f}" % gm["qdare_vs_vida_video_throughput"],
        "\\newcommand{\\QDAREViDAreaGeo}{%.2f}" % gm["qdare_vs_vida_area_efficiency"],
        "\\newcommand{\\QDAREAreaGeoA}{%.2f}" % gm["qdare_vs_a100_area_efficiency"],
        "\\newcommand{\\ViDAThroughputGeoA}{%.2f}" % gm["vida_vs_a100_video_throughput"],
        "\\newcommand{\\ViDAreaGeoA}{%.2f}" % VIDA_AREA_EFFICIENCY_VS_A100,
        "\\newcommand{\\AOneHundredQDAREBarRows}{%",
    ]
    for row in rows:
        lines.append(
            "  %d & %.3f & %.3f & %.5f & %.5f \\\\" % (
                row["frames"], row["a100_steps_per_s"],
                row["qdare_steps_per_s"], row["a100_steps_per_s_per_w"],
                row["qdare_steps_per_s_per_w"],
            )
        )
    lines.extend(["}", "\\newcommand{\\ViDAComparisonRows}{%"])
    for row in rows:
        lines.append(
            "  %d & %.2f$\\times$ & %.2f$\\times$ & %.3f$\\times$ \\\\" % (
                row["frames"], row["qdare_vs_a100_video_throughput"],
                row["vida_a100_speedup"],
                row["qdare_vs_vida_video_throughput"],
            )
        )
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_readme(path, rows, data):
    gm = data["geomeans"]
    lines = [
        "# Hardware comparison data", "",
        "The A100 numbers are measured STDiT-backbone results. Q-DARE uses",
        "the optimized cycle-level schedule selected for the paper.", "",
        "## Latency and video throughput", "",
        "| Frames | A100 latency | Q-DARE latency | ViDA latency (derived) | Q-DARE/A100 | Q-DARE/ViDA |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {frames} | {a100_latency_s:.3f} s | "
            "{qdare_latency_s_cycle_model:.3f} s | "
            "{vida_latency_s_derived:.3f} s | "
            "{qdare_vs_a100_video_throughput:.2f}x | "
            "{qdare_vs_vida_video_throughput:.3f}x |".format(**row))
    lines.extend([
        "| Geomean | -- | -- | -- | %.2fx | %.2fx |" % (
            gm["qdare_vs_a100_video_throughput"],
            gm["qdare_vs_vida_video_throughput"]),
        "", "## A100 figure data", "",
        "| Frames | A100 steps/s | Q-DARE steps/s | A100 steps/s/kW | Q-DARE steps/s/kW | Throughput gain | Energy-efficiency gain |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in rows:
        lines.append(
            "| {frames} | {a100_steps_per_s:.3f} | {qdare_steps_per_s:.3f} | "
            "{a100_steps_per_s_per_kw:.3f} | {qdare_steps_per_s_per_kw:.3f} | "
            "{qdare_vs_a100_step_throughput:.2f}x | "
            "{qdare_vs_a100_step_energy_efficiency:.1f}x |".format(**row))
    lines.extend([
        "| Geomean | %.3f | %.3f | %.3f | %.3f | %.2fx | %.1fx |" % (
            gm["a100_steps_per_s"], gm["qdare_steps_per_s"],
            gm["a100_steps_per_s_per_kw"],
            gm["qdare_steps_per_s_per_kw"],
            gm["qdare_vs_a100_step_throughput"],
            gm["qdare_vs_a100_step_energy_efficiency"]),
        "", "## ViDA-normalized results", "",
        "| Metric | Q-DARE/ViDA |", "|---|---:|",
    ])
    for row in rows:
        lines.append("| %dF video throughput | %.3fx |" % (
            row["frames"], row["qdare_vs_vida_video_throughput"]))
    lines.extend([
        "| Video-throughput geomean | %.2fx |" %
        gm["qdare_vs_vida_video_throughput"],
        "| Area-efficiency geomean | %.2fx |" %
        gm["qdare_vs_vida_area_efficiency"],
        "", "The ViDA ratios use its reported A100-relative results. The",
        "Q-DARE/ViDA ratios divide the corresponding A100-relative metrics.",
        "", "## PPA", "",
        "| Quantity | Value |", "|---|---:|",
        "| Q-DARE per-core 7nm area | %.3f mm^2 |" % QDARE_CORE_AREA_7NM_MM2,
        "| Q-DARE per-core 7nm power | %.1f mW |" % QDARE_CORE_POWER_7NM_MW,
        "| Complete-configuration 7nm area | %.3f mm^2 |" % QDARE_AREA_7NM_MM2,
        "| Complete-configuration 7nm power | %.3f W |" % QDARE_POWER_7NM_W,
        "| A100 die area | %.1f mm^2 |" % A100_AREA_MM2,
        "| ViDA 7nm area | %.2f mm^2 |" % VIDA_AREA_7NM_MM2,
        "", "PPA is technology-normalized from the available 28nm results.",
        "NoC, clock tree, I/O, shared memory, and DRAM overhead are not included;",
        "the mapped source netlist also omits the complete PEA datapath.",
        "", "Run `python3 scripts/build_hardware_comparison.py` from the repository root.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    rows = load_rows()
    data = build_summary(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEX_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_csv(OUTPUT_DIR / "hardware_comparison.csv", rows)
    (OUTPUT_DIR / "hardware_comparison.json").write_text(
        json.dumps({"summary": data, "workloads": rows}, indent=2) + "\n",
        encoding="utf-8")
    write_readme(OUTPUT_DIR / "README.md", rows, data)
    write_tex(TEX_OUTPUT, rows, data)
    print("wrote %s" % OUTPUT_DIR)
    print("wrote %s" % TEX_OUTPUT)


if __name__ == "__main__":
    main()
