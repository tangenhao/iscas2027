#!/usr/bin/env python3
"""Build a ViDA/A100/Q-DARE comparison workbook from the paper data."""

import json
import os
import re
import stat
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "data" / "vs_A100.xlsx"
RESULTS = ROOT / "data" / "hardware_comparison" / "hardware_comparison.json"
OUTPUT = ROOT / "data" / "vs_ViDA.xlsx"

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
ET.register_namespace("", MAIN_NS)


def number(value):
    return format(float(value), ".15g")


def cell_pattern(reference):
    return re.compile(
        r'<c\b(?P<attrs>[^>]*\br="%s"[^>]*)>(?P<body>.*?)</c>'
        % re.escape(reference),
        re.DOTALL,
    )


def set_numeric_cell(xml, reference, value, style=None):
    self_closing = re.compile(
        r'<c\b(?P<attrs>[^>]*\br="%s"[^>]*)/>' % re.escape(reference)
    )

    def expand(match):
        attrs = re.sub(r'\s+t="[^"]*"', "", match.group("attrs"))
        if style is not None:
            if re.search(r'\s+s="[^"]*"', attrs):
                attrs = re.sub(r'\s+s="[^"]*"', ' s="%s"' % style, attrs)
            else:
                attrs += ' s="%s"' % style
        return '<c%s><v>%s</v></c>' % (attrs, number(value))

    updated, count = self_closing.subn(expand, xml, count=1)
    if count == 1:
        return updated

    pattern = cell_pattern(reference)

    def replacement(match):
        attrs = re.sub(r'\s+t="[^"]*"', "", match.group("attrs"))
        if style is not None:
            if re.search(r'\s+s="[^"]*"', attrs):
                attrs = re.sub(r'\s+s="[^"]*"', ' s="%s"' % style, attrs)
            else:
                attrs += ' s="%s"' % style
        body = re.sub(r'<f\b[^>]*>.*?</f>', "", match.group("body"),
                      flags=re.DOTALL)
        body = re.sub(r'<f\b[^>]*/>', "", body)
        body = re.sub(r'<v>.*?</v>', "", body, flags=re.DOTALL)
        return '<c%s>%s<v>%s</v></c>' % (attrs, body, number(value))

    updated, count = pattern.subn(replacement, xml, count=1)
    if count != 1:
        raise RuntimeError("could not update cell %s" % reference)
    return updated


def clear_cell(xml, reference):
    pattern = cell_pattern(reference)

    def replacement(match):
        body = re.sub(r'<f\b[^>]*>.*?</f>', "", match.group("body"),
                      flags=re.DOTALL)
        body = re.sub(r'<f\b[^>]*/>', "", body)
        body = re.sub(r'<v>.*?</v>', "", body, flags=re.DOTALL)
        return '<c%s>%s</c>' % (match.group("attrs"), body)

    updated, count = pattern.subn(replacement, xml, count=1)
    if count != 1:
        raise RuntimeError("could not clear cell %s" % reference)
    return updated


def set_shared_string_cell(xml, reference, index):
    pattern = cell_pattern(reference)

    def replacement(match):
        attrs = match.group("attrs")
        if re.search(r'\s+t="[^"]*"', attrs):
            attrs = re.sub(r'\s+t="[^"]*"', ' t="s"', attrs)
        else:
            attrs += ' t="s"'
        body = re.sub(r'<v>.*?</v>', "", match.group("body"),
                      flags=re.DOTALL)
        return '<c%s>%s<v>%d</v></c>' % (attrs, body, index)

    updated, count = pattern.subn(replacement, xml, count=1)
    if count != 1:
        raise RuntimeError("could not update shared-string cell %s" % reference)
    return updated


def remove_cells(xml, references):
    for reference in references:
        pattern = cell_pattern(reference)
        xml, count = pattern.subn("", xml, count=1)
        if count != 1:
            raise RuntimeError("could not remove helper cell %s" % reference)
    return xml


def append_cell_to_row(xml, row_number, cell_xml):
    pattern = re.compile(
        r'(<row\b[^>]*\br="%s"[^>]*>.*?)(</row>)' % row_number,
        re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: match.group(1) + cell_xml + match.group(2),
        xml,
        count=1,
    )
    if count != 1:
        raise RuntimeError("could not append to row %s" % row_number)
    return updated


def append_row(xml, row_xml):
    marker = "</sheetData>"
    if marker not in xml:
        raise RuntimeError("worksheet has no sheetData")
    return xml.replace(marker, row_xml + marker, 1)


def update_shared_strings(content):
    strings = [
        "Frames",
        "A100 Latency (s)",
        "ViDA Latency (s, derived)",
        "Q-DARE Latency (s)",
        "ViDA/A100 Video Throughput (×)",
        "Q-DARE/A100 Video Throughput (×)",
        "Q-DARE/ViDA Video Throughput (×)",
        "Geomean",
        "ViDA",
        "Q-DARE",
        "A100",
        "ViDA",
        "ViDA",
        "ViDA/Q-DARE Video Throughput (×)",
        "Q-DARE/A100 Area Efficiency (×)",
        "ViDA/A100 Area Efficiency (×)",
        "Q-DARE/ViDA Area Efficiency (×)",
        "Area-efficiency calculation",
        "Q-DARE/A100 = video-throughput ratio × (A100 area / Q-DARE area)",
        "Q-DARE/ViDA = Q-DARE/A100 area efficiency / ViDA/A100 area efficiency",
        "ViDA reports only a geomean area-efficiency ratio; per-workload values are unavailable.",
    ]
    root = ET.fromstring(content)
    entries = root.findall("{%s}si" % MAIN_NS)
    if len(entries) > len(strings):
        raise RuntimeError("unexpected shared-string count")
    for entry, value in zip(entries, strings):
        nodes = entry.findall(".//{%s}t" % MAIN_NS)
        if not nodes:
            raise RuntimeError("shared-string entry has no text node")
        nodes[0].text = value
        for node in nodes[1:]:
            node.text = ""
    for value in strings[len(entries):]:
        entry = ET.SubElement(root, "{%s}si" % MAIN_NS)
        node = ET.SubElement(entry, "{%s}t" % MAIN_NS)
        node.text = value
    root.attrib["count"] = str(len(strings))
    root.attrib["uniqueCount"] = str(len(strings))
    return (b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' +
            ET.tostring(root, encoding="utf-8"))


def update_chart_cache(xml, series_values):
    cache_pattern = re.compile(r"<c:numCache>.*?</c:numCache>", re.DOTALL)
    caches = cache_pattern.findall(xml)
    if len(caches) != len(series_values):
        raise RuntimeError("unexpected number of chart caches")
    replacements = []
    for cache, values in zip(caches, series_values):
        values = iter(number(value) for value in values)

        def replace_value(match):
            try:
                value = next(values)
            except StopIteration:
                raise RuntimeError("chart cache contains too many values")
            return match.group(1) + value + match.group(2)

        updated, count = re.subn(
            r"(<c:v>)[^<]*(</c:v>)", replace_value, cache
        )
        try:
            next(values)
            raise RuntimeError("chart cache contains too few values")
        except StopIteration:
            pass
        if count == 0:
            raise RuntimeError("empty chart cache")
        replacements.append(updated)
    replacements = iter(replacements)
    return cache_pattern.sub(lambda _: next(replacements), xml)


def main():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = data["workloads"]
    geomeans = data["summary"]["geomeans"]
    if [row["frames"] for row in rows] != [64, 256, 512]:
        raise RuntimeError("unexpected workload order")

    vida_a100 = [row["vida_a100_speedup"] for row in rows]
    qdare_a100 = [row["qdare_vs_a100_video_throughput"] for row in rows]
    qdare_vida = [row["qdare_vs_vida_video_throughput"] for row in rows]
    vida_qdare = [1.0 / value for value in qdare_vida]
    vida_a100_geo = geomeans["vida_vs_a100_video_throughput"]
    qdare_a100_geo = geomeans["qdare_vs_a100_video_throughput"]
    qdare_vida_geo = geomeans["qdare_vs_vida_video_throughput"]
    vida_qdare_geo = 1.0 / qdare_vida_geo
    qdare_area = [row["qdare_vs_a100_area_efficiency"] for row in rows]
    qdare_area_geo = geomeans["qdare_vs_a100_area_efficiency"]
    vida_area_geo = data["summary"]["vida"][
        "reported_a100_area_efficiency_geomean"
    ]
    qdare_vida_area_geo = geomeans["qdare_vs_vida_area_efficiency"]

    with ZipFile(TEMPLATE, "r") as source:
        members = {item.filename: (item, source.read(item.filename))
                   for item in source.infolist()}

    sheet1 = members["xl/worksheets/sheet1.xml"][1].decode("utf-8")
    for index, row in enumerate(rows, start=2):
        values = {
            "B%d" % index: row["a100_latency_s"],
            "C%d" % index: row["vida_latency_s_derived"],
            "D%d" % index: row["qdare_latency_s_cycle_model"],
            "E%d" % index: row["vida_a100_speedup"],
            "F%d" % index: row["qdare_vs_a100_video_throughput"],
            "G%d" % index: row["qdare_vs_vida_video_throughput"],
        }
        for reference, value in values.items():
            style = "5" if reference[0] in "BCEFG" else "6"
            sheet1 = set_numeric_cell(sheet1, reference, value, style)
    sheet1 = clear_cell(sheet1, "D5")
    sheet1 = set_numeric_cell(sheet1, "E5", vida_a100_geo, "11")
    sheet1 = set_numeric_cell(sheet1, "F5", qdare_a100_geo, "11")
    sheet1 = set_numeric_cell(sheet1, "G5", qdare_vida_geo, "11")

    sheet2 = members["xl/worksheets/sheet2.xml"][1].decode("utf-8")
    sheet2 = set_shared_string_cell(sheet2, "D1", 4)
    for index, value in enumerate(vida_a100, start=2):
        sheet2 = set_numeric_cell(sheet2, "B%d" % index, 1.0, "5")
        sheet2 = set_numeric_cell(sheet2, "C%d" % index, value, "5")
        sheet2 = set_numeric_cell(sheet2, "D%d" % index, value, "5")
        sheet2 = set_numeric_cell(sheet2, "B%d" % (index + 6), 1.0, "13")
        sheet2 = set_numeric_cell(sheet2, "C%d" % (index + 6), value, "13")
    sheet2 = set_numeric_cell(sheet2, "B5", 1.0, "11")
    sheet2 = set_numeric_cell(sheet2, "C5", vida_a100_geo, "11")
    sheet2 = set_numeric_cell(sheet2, "D5", vida_a100_geo, "11")
    sheet2 = set_numeric_cell(sheet2, "B11", 1.0, "13")
    sheet2 = set_numeric_cell(sheet2, "C11", vida_a100_geo, "11")

    sheet3 = members["xl/worksheets/sheet3.xml"][1].decode("utf-8")
    sheet3 = set_shared_string_cell(sheet3, "B9", 14)
    sheet3 = set_shared_string_cell(sheet3, "C9", 15)
    sheet3 = set_shared_string_cell(sheet3, "D9", 16)
    for index, (forward, area_value) in enumerate(
            zip(qdare_vida, qdare_area), start=2):
        sheet3 = set_numeric_cell(sheet3, "B%d" % index, 1.0, "5")
        sheet3 = set_numeric_cell(sheet3, "C%d" % index, forward, "5")
        sheet3 = set_numeric_cell(sheet3, "D%d" % index, forward, "5")
        sheet3 = set_numeric_cell(sheet3, "B%d" % (index + 8), area_value,
                                  "13")
        sheet3 = clear_cell(sheet3, "C%d" % (index + 8))
        sheet3 = clear_cell(sheet3, "D%d" % (index + 8))
    sheet3 = set_numeric_cell(sheet3, "B5", 1.0, "11")
    sheet3 = set_numeric_cell(sheet3, "C5", qdare_vida_geo, "11")
    sheet3 = set_numeric_cell(sheet3, "D5", qdare_vida_geo, "11")
    sheet3 = set_numeric_cell(sheet3, "B13", qdare_area_geo, "13")
    sheet3 = set_numeric_cell(sheet3, "C13", vida_area_geo, "11")
    sheet3 = set_numeric_cell(sheet3, "D13", qdare_vida_area_geo, "11")
    sheet3 = remove_cells(
        sheet3,
        [column + str(row) for row in range(2, 5) for column in "FGH"],
    )
    sheet3 = sheet3.replace('dimension ref="A1:H13"',
                            'dimension ref="A1:D13"')
    sheet3 = append_row(
        sheet3,
        '<row r="15"><c r="A15" t="s"><v>17</v></c></row>',
    )
    sheet3 = append_row(
        sheet3,
        '<row r="16"><c r="A16" t="s"><v>18</v></c></row>',
    )
    sheet3 = append_row(
        sheet3,
        '<row r="17"><c r="A17" t="s"><v>19</v></c></row>',
    )
    sheet3 = append_row(
        sheet3,
        '<row r="18"><c r="A18" t="s"><v>20</v></c></row>',
    )
    sheet3 = sheet3.replace('dimension ref="A1:D13"',
                            'dimension ref="A1:D18"')

    chart1 = members["xl/charts/chart1.xml"][1].decode("utf-8")
    chart1 = chart1.replace("Throughput!", "ViDA_vs_A100!")
    chart1 = chart1.replace("<c:v>Q-DARE </c:v>", "<c:v>ViDA</c:v>")
    chart1 = update_chart_cache(
        chart1, [[1.0] * 4, vida_a100 + [vida_a100_geo]]
    )
    chart1 = chart1.replace(
        '<c:scaling><c:orientation val="minMax"/><c:min val="0"/></c:scaling>',
        '<c:scaling><c:orientation val="minMax"/><c:max val="20"/><c:min val="0"/></c:scaling>',
        1,
    ).replace('<c:majorUnit val="1"/>', '<c:majorUnit val="5"/>', 1)

    chart2 = members["xl/charts/chart2.xml"][1].decode("utf-8")
    chart2 = chart2.replace("EE!", "ViDA_vs_QDARE!")
    chart2 = chart2.replace("<c:v>A100 </c:v>", "<c:v>ViDA</c:v>")
    chart2 = chart2.replace("ViDA_vs_QDARE!$B$9", "ViDA_vs_QDARE!$B$1")
    chart2 = chart2.replace("ViDA_vs_QDARE!$C$9", "ViDA_vs_QDARE!$C$1")
    chart2 = chart2.replace("ViDA_vs_QDARE!$A$10:$A$13",
                            "ViDA_vs_QDARE!$A$2:$A$5")
    chart2 = chart2.replace("ViDA_vs_QDARE!$B$10:$B$13",
                            "ViDA_vs_QDARE!$B$2:$B$5")
    chart2 = chart2.replace("ViDA_vs_QDARE!$C$10:$C$13",
                            "ViDA_vs_QDARE!$C$2:$C$5")
    chart2 = update_chart_cache(
        chart2, [[1.0] * 4, qdare_vida + [qdare_vida_geo]]
    )
    chart2 = chart2.replace('<c:max val="400"/>', '<c:max val="1.2"/>', 1)
    chart2 = chart2.replace('<c:majorUnit val="100"/>',
                            '<c:majorUnit val="0.2"/>', 1)
    chart2 = chart2.replace('<c:minorUnit val="50"/>',
                            '<c:minorUnit val="0.1"/>', 1)

    workbook = members["xl/workbook.xml"][1].decode("utf-8")
    workbook = workbook.replace('name="Sheet1"', 'name="Summary"', 1)
    workbook = workbook.replace('name="Throughput"',
                                'name="ViDA_vs_A100"', 1)
    workbook = workbook.replace('name="EE"', 'name="ViDA_vs_QDARE"', 1)

    updates = {
        "xl/sharedStrings.xml": update_shared_strings(
            members["xl/sharedStrings.xml"][1]
        ),
        "xl/workbook.xml": workbook.encode("utf-8"),
        "xl/worksheets/sheet1.xml": sheet1.encode("utf-8"),
        "xl/worksheets/sheet2.xml": sheet2.encode("utf-8"),
        "xl/worksheets/sheet3.xml": sheet3.encode("utf-8"),
        "xl/charts/chart1.xml": chart1.encode("utf-8"),
        "xl/charts/chart2.xml": chart2.encode("utf-8"),
    }

    original_mode = stat.S_IMODE(TEMPLATE.stat().st_mode)
    handle, temporary_name = tempfile.mkstemp(
        prefix="vs_ViDA.", suffix=".xlsx", dir=str(OUTPUT.parent)
    )
    os.close(handle)
    try:
        with ZipFile(temporary_name, "w", compression=ZIP_DEFLATED) as target:
            for name, (info, content) in members.items():
                target.writestr(info, updates.get(name, content))
        os.chmod(temporary_name, original_mode)
        os.replace(temporary_name, OUTPUT)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)

    print("wrote %s" % OUTPUT)
    print("ViDA/A100 three-workload geomean: %.2fx" % vida_a100_geo)
    print("Q-DARE/ViDA geomean: %.2fx" % qdare_vida_geo)
    print("Q-DARE/ViDA area-efficiency geomean: %.2fx" %
          geomeans["qdare_vs_vida_area_efficiency"])


if __name__ == "__main__":
    main()
