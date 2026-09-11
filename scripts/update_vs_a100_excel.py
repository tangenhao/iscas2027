#!/usr/bin/env python3
"""Update the existing A100 comparison workbook from generated results."""

import json
import os
import re
import stat
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "vs_A100.xlsx"
RESULTS = ROOT / "data" / "hardware_comparison" / "hardware_comparison.json"


def number(value):
    return format(float(value), ".15g")


def replace_cell(xml, reference, value):
    pattern = re.compile(
        r'(<c\b[^>]*\br="%s"[^>]*>.*?<v>)[^<]*(</v>)'
        % re.escape(reference),
        re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: match.group(1) + number(value) + match.group(2),
        xml,
        count=1,
    )
    if count != 1:
        raise RuntimeError("could not update cell %s" % reference)
    return updated


def update_cells(xml, values):
    for reference, value in values.items():
        xml = replace_cell(xml, reference, value)
    return xml


def update_chart_cache(xml, series_values):
    cache_pattern = re.compile(r"<c:numCache>.*?</c:numCache>", re.DOTALL)
    caches = cache_pattern.findall(xml)
    if len(caches) != len(series_values):
        raise RuntimeError(
            "expected %d chart caches, found %d"
            % (len(series_values), len(caches))
        )

    replacements = []
    value_pattern = re.compile(r"(<c:v>)[^<]*(</c:v>)")
    for cache, values in zip(caches, series_values):
        formatted = iter(number(value) for value in values)

        def replace_value(match):
            try:
                value = next(formatted)
            except StopIteration:
                raise RuntimeError("chart cache contains too many values")
            return match.group(1) + value + match.group(2)

        updated, count = value_pattern.subn(replace_value, cache)
        try:
            next(formatted)
            raise RuntimeError("chart cache contains too few values")
        except StopIteration:
            pass
        if count != len(values):
            raise RuntimeError("unexpected chart cache size")
        replacements.append(updated)

    replacement_iter = iter(replacements)
    return cache_pattern.sub(lambda _: next(replacement_iter), xml)


def update_energy_axis(xml):
    xml = xml.replace('<c:max val="140"/>', '<c:max val="400"/>', 1)
    if '<c:max val="400"/>' not in xml:
        raise RuntimeError("could not update energy-efficiency chart axis")
    xml = xml.replace('<c:majorUnit val="30"/>', '<c:majorUnit val="100"/>', 1)
    if '<c:majorUnit val="100"/>' not in xml:
        raise RuntimeError("could not update energy-efficiency major tick")
    xml = xml.replace('<c:minorUnit val="10"/>', '<c:minorUnit val="50"/>', 1)
    if '<c:minorUnit val="50"/>' not in xml:
        raise RuntimeError("could not update energy-efficiency minor tick")
    return xml


def main():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = data["workloads"]
    geomeans = data["summary"]["geomeans"]
    if [row["frames"] for row in rows] != [64, 256, 512]:
        raise RuntimeError("unexpected workload order")

    throughput = [row["qdare_vs_a100_step_throughput"] for row in rows]
    energy = [
        row["qdare_vs_a100_step_energy_efficiency"] for row in rows
    ]
    throughput_geomean = geomeans["qdare_vs_a100_step_throughput"]
    energy_geomean = geomeans["qdare_vs_a100_step_energy_efficiency"]

    sheet1 = {}
    sheet2 = {}
    sheet3 = {}
    for index, row in enumerate(rows, start=2):
        sheet1.update({
            "B%d" % index: row["a100_steps_per_s"],
            "C%d" % index: row["qdare_steps_per_s"],
            "D%d" % index: row["qdare_vs_a100_step_throughput"],
            "E%d" % index: row["a100_steps_per_s_per_w"],
            "F%d" % index: row["qdare_steps_per_s_per_w"],
            "G%d" % index: row["qdare_vs_a100_step_energy_efficiency"],
        })
        sheet2.update({
            "B%d" % index: row["a100_steps_per_s"],
            "C%d" % index: row["qdare_steps_per_s"],
            "D%d" % index: row["qdare_vs_a100_step_throughput"],
            "B%d" % (index + 6): 1.0,
            "C%d" % (index + 6): row["qdare_vs_a100_step_throughput"],
        })
        sheet3.update({
            "B%d" % index: row["a100_steps_per_s_per_kw"],
            "C%d" % index: row["qdare_steps_per_s_per_kw"],
            "D%d" % index: row["qdare_vs_a100_step_energy_efficiency"],
            "F%d" % index: row["a100_steps_per_s_per_w"],
            "G%d" % index: row["qdare_steps_per_s_per_w"],
            "H%d" % index: row["qdare_vs_a100_step_energy_efficiency"],
            "B%d" % (index + 8): 1.0,
            "C%d" % (index + 8): row["qdare_vs_a100_step_energy_efficiency"],
            "D%d" % (index + 8): row["qdare_vs_a100_step_energy_efficiency"],
        })

    sheet1.update({"D5": throughput_geomean, "G5": energy_geomean})
    sheet2.update({"D5": throughput_geomean, "B11": 1.0,
                   "C11": throughput_geomean})
    sheet3.update({"D5": energy_geomean, "B13": 1.0,
                   "C13": energy_geomean, "D13": energy_geomean})

    original_mode = stat.S_IMODE(WORKBOOK.stat().st_mode)
    with ZipFile(WORKBOOK, "r") as source:
        members = {item.filename: (item, source.read(item.filename))
                   for item in source.infolist()}

    updates = {
        "xl/worksheets/sheet1.xml": update_cells(
            members["xl/worksheets/sheet1.xml"][1].decode("utf-8"),
            sheet1,
        ).encode("utf-8"),
        "xl/worksheets/sheet2.xml": update_cells(
            members["xl/worksheets/sheet2.xml"][1].decode("utf-8"),
            sheet2,
        ).encode("utf-8"),
        "xl/worksheets/sheet3.xml": update_cells(
            members["xl/worksheets/sheet3.xml"][1].decode("utf-8"),
            sheet3,
        ).encode("utf-8"),
        "xl/charts/chart1.xml": update_chart_cache(
            members["xl/charts/chart1.xml"][1].decode("utf-8"),
            [[1.0] * 4, throughput + [throughput_geomean]],
        ).encode("utf-8"),
        "xl/charts/chart2.xml": update_energy_axis(update_chart_cache(
            members["xl/charts/chart2.xml"][1].decode("utf-8"),
            [[1.0] * 4, energy + [energy_geomean]],
        )).encode("utf-8"),
    }

    workbook_xml = members["xl/workbook.xml"][1].decode("utf-8")
    workbook_xml, count = re.subn(
        r"<calcPr\b[^>]*/>",
        '<calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/>',
        workbook_xml,
        count=1,
    )
    if count != 1:
        raise RuntimeError("could not update workbook calculation settings")
    updates["xl/workbook.xml"] = workbook_xml.encode("utf-8")

    handle, temporary_name = tempfile.mkstemp(
        prefix="vs_A100.", suffix=".xlsx", dir=str(WORKBOOK.parent)
    )
    os.close(handle)
    try:
        with ZipFile(temporary_name, "w", compression=ZIP_DEFLATED) as target:
            for name, (info, content) in members.items():
                target.writestr(info, updates.get(name, content))
        os.chmod(temporary_name, original_mode)
        os.replace(temporary_name, WORKBOOK)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    print("updated %s" % WORKBOOK)
    print("throughput geomean: %.2fx" % throughput_geomean)
    print("energy-efficiency geomean: %.1fx" % energy_geomean)


if __name__ == "__main__":
    main()
