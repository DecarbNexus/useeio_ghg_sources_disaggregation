"""
Extract EPA GHGI metadata from FlowSA YAML configuration.

This script parses the EPA_GHGI.yaml file from the FlowSA package and extracts
table metadata including meta_id, chapter, table_id, and description fields.

By default, only basic metadata is extracted (meta_id, chapter, table_id, desc).
Legacy IPCC_Category and Subcategory fields are disabled by default but can be
enabled with the --extract-categories flag.

Usage:
    # Basic metadata extraction (default)
    python extract_meta_from_EPA_GHGI.py
    
    # Include legacy IPCC_Category and Subcategory fields
    python extract_meta_from_EPA_GHGI.py --extract-categories
    
    # Custom input/output paths
    python extract_meta_from_EPA_GHGI.py --input path/to/EPA_GHGI.yaml --csv-out outputs/meta.csv

Output:
    - CSV: Flattened table with one row per EPA GHGI table
    - YAML: Keyed map with meta_id as keys for easy lookup
"""
from __future__ import annotations
import os
import re
from typing import Any, Dict, Iterable, List, Tuple

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# Input YAML (installed package file)
DEFAULT_INPUT = r".\\.venv\\Lib\\site-packages\\flowsa\\methods\\flowbyactivitymethods\\EPA_GHGI.yaml"

# Outputs
CSV_OUT = os.path.join("outputs", "metadata", "EPA_GHGI_meta_sources.csv")
YAML_OUT = os.path.join("outputs", "metadata", "EPA_GHGI_meta_sources.yaml")

# Optional custom replacements to tweak resulting category labels. Each entry is
# a (compiled_regex, replacement) pair applied in order. Users can extend this list
# as needed or provide a label map CSV via --label-map.
CUSTOM_DESC_TRANSFORMS: List[Tuple[re.Pattern, str]] = [
    # Remove leading "<gas list> Emissions from " (supports commas and 'and')
    (re.compile(r"^[A-Za-z0-9,\-\s]+?\s+Emissions\s+from\s+", re.IGNORECASE), ""),
    # Also handle plain "Emissions from " just in case
    (re.compile(r"^Emissions\s+from\s+", re.IGNORECASE), ""),
    # Remove "Production of "
    (re.compile(r"\bProduction\s+of\s+", re.IGNORECASE), ""),
    # Remove specific greenhouse gas list phrase
    (re.compile(r"Emissions\s+of\s+HFCs,\s+PFCs,\s+SF6,\s+and\s+NF3\s+from\s+", re.IGNORECASE), ""),
    (re.compile(r"Emissions\s+of\s+HFCs,\s*PFCs,\s*and\s*CO2\s+from\s+", re.IGNORECASE), ""),
    # Remove trailing qualifiers
    (re.compile(r"\bEnd-Use\s+Sector\b", re.IGNORECASE), ""),
    (re.compile(r"\bby\s+Fuel\s+Type\b", re.IGNORECASE), ""),
    (re.compile(r"Consumption\s+by\s+Fuel\s+and\s+Vehicle\s+Type", re.IGNORECASE), ""),
    # Remove leading year-specific qualifier and generic "Adjusted " at start
    (re.compile(r"^\s*[0-9]+\s+Adjusted\s+", re.IGNORECASE), ""),
    (re.compile(r"^\s*Adjusted\s+", re.IGNORECASE), ""),
    # Normalize specific phrases
    (re.compile(r"\bStationary\s+Fossil\s+Fuel\s+Combustion\b", re.IGNORECASE), "Stationary Combustion"),
]


def _iter_tables(data: Dict[str, Any]) -> Iterable[Tuple[str, str, str, Dict[str, Any]]]:
    """
    Yield tuples of (section, chapter, table_id, table_spec) for both Tables and Annex sections.
    section: one of "Tables" or "Annex"
    chapter: e.g., "Chapter 3 - Energy" or "Annex 2"
    table_id: e.g., "3-68" or "A-9"
    table_spec: dict for that table
    """
    for section in ("Tables", "Annex"):
        section_map = data.get(section)
        if not isinstance(section_map, dict):
            continue
        for chapter, chapter_map in section_map.items():
            if not isinstance(chapter_map, dict):
                continue
            for table_id, spec in chapter_map.items():
                if isinstance(spec, dict):
                    yield section, str(chapter), str(table_id), spec


def _parse_desc(raw_desc: Any) -> Tuple[str, str, str]:
    """
    Parse a desc value into (table_ref, description, trailing_unit_in_parens).
    - table_ref: leading "Table X" portion if present, else ""
    - description: remainder after ':' with trailing parentheses removed
    - trailing_unit_in_parens: text inside the final (...) if present at the end
    """
    if raw_desc is None:
        return "", "", ""

    # Join multiline block scalars or non-strings into a single string
    if isinstance(raw_desc, (list, tuple)):
        desc = " ".join(str(x) for x in raw_desc)
    else:
        desc = str(raw_desc)

    desc = desc.strip().replace("\n", " ")

    # Capture trailing unit in parentheses e.g., "... (MMT CO2 Eq.)"
    unit_paren = ""
    m_unit = re.search(r"\s*\(([^()]*)\)\s*$", desc)
    if m_unit:
        unit_paren = m_unit.group(1).strip()
        desc_wo_unit = desc[: m_unit.start()].rstrip()
    else:
        desc_wo_unit = desc

    # Split at the first ':' to separate table ref
    table_ref = ""
    description = desc_wo_unit

    # If it starts with "Table ...:" capture that part as table_ref
    m_table = re.match(r"^\s*(Table\s+[A-Za-z]?-?\d+(?:-\d+)?)\s*:\s*(.*)$", desc_wo_unit)
    if m_table:
        table_ref = m_table.group(1).strip()
        description = m_table.group(2).strip()
    else:
        # If some other colon exists, split on the first colon as a fallback
        parts = desc_wo_unit.split(":", 1)
        if len(parts) == 2:
            table_ref = parts[0].strip()
            description = parts[1].strip()

    return table_ref, description, unit_paren


def _clean_category(description: str) -> str:
    """Apply normalization rules to build the GHG source category label.
    - Remove leading patterns like "CO2 Emissions from ", "CH4 and N2O Emissions from ", etc.
    - Remove phrases: "End-Use Sector", "Production of ", "by Fuel Type",
      "Consumption by Fuel and Vehicle Type".
    - Collapse whitespace and stray commas.
    """
    s = description or ""
    for pat, repl in CUSTOM_DESC_TRANSFORMS:
        s = pat.sub(repl, s)
    # Collapse ODS Substitutes sector phrasing to just "ODS Substitutes"
    s = re.sub(r"\bODS\s+Substitutes\s*(?:\([^)]*\))?\s*by\s+Sector\b", "ODS Substitutes", s, flags=re.IGNORECASE)

    # Remove extra spaces around punctuation and collapse spaces
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+,\s+", ", ", s)
    # Remove dangling trailing 'by'
    s = re.sub(r"\bby\s*$", "", s, flags=re.IGNORECASE)
    # Strip stray quotes and punctuation at ends
    s = s.strip(" \"' ,.-")

    # Remove the Chapter 2 summary label entirely
    if s.lower() == "recent trends in u.s. greenhouse gas emissions and sinks":
        s = ""
    return s


def _normalize_raw_desc(raw_desc: Any) -> str:
    """Return the original desc as a single line, preserving text but stripping newlines."""
    if raw_desc is None:
        return ""
    if isinstance(raw_desc, (list, tuple)):
        desc = " ".join(str(x) for x in raw_desc)
    else:
        desc = str(raw_desc)
    return desc.strip().replace("\n", " ")


def _compute_ipcc_category(chapter: str, desc: str | None = None) -> str:
    """Extract an IPCC-like top-level category from the chapter string.
    - If format is "Chapter N - Name", returns Name (except for Chapter 2, returns empty string).
    - If it starts with "Annex", return mapped categories:
        * Annex 2 -> Energy
        * Annex 3 -> conditional overrides by desc, else keep chapter as-is
    - Otherwise, return empty string.
    """
    if not chapter:
        return ""
    chapter = str(chapter).strip()
    # Annex special cases
    lower_chap = chapter.lower()
    if lower_chap.startswith("annex 2"):
        return "Energy"
    if lower_chap.startswith("annex 3"):
        d = (desc or "")
        if "HFC Emissions from Transportation Sources" in d:
            return "Industrial Processes and Product Use"
        if "Fuel Consumption by Fuel and Vehicle Type" in d:
            return "Energy"
        return chapter
    m = re.match(r"^Chapter\s+(\d+)\s*-\s*(.+)$", chapter, flags=re.IGNORECASE)
    if m:
        num = m.group(1)
        name = m.group(2).strip()
        if num == "2":
            return ""  # explicitly exclude Chapter 2 as requested
        return name
    # Keep Annex value as-is if any other Annex
    if chapter.lower().startswith("annex"):
        return chapter
    return ""


def _to_meta_id(table_id: str) -> str:
    # e.g., "3-68" -> "EPA_GHGI_T_3_68" ; "A-9" -> "EPA_GHGI_T_A_9"
    return f"EPA_GHGI_T_{table_id.replace('-', '_')}"


def build_meta_rows(input_yaml: str, extract_categories: bool = False) -> List[Dict[str, Any]]:
    yaml = YAML()
    with open(input_yaml, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    rows: List[Dict[str, Any]] = []

    for section, chapter, table_id, spec in _iter_tables(data):
        meta_id = _to_meta_id(table_id)
        raw_desc = spec.get("desc")
        original_desc = _normalize_raw_desc(raw_desc)

        row = {
            "meta_id": meta_id,
            "chapter": chapter,
            "table_id": table_id,
            "desc": original_desc,
        }

        # Only extract categories if explicitly requested
        if extract_categories:
            table_ref, description, _desc_unit = _parse_desc(raw_desc)
            ghg_category = _clean_category(description)
            # Derive IPCC category from chapter string
            ipcc_category = _compute_ipcc_category(chapter, original_desc)
            row["IPCC_Category"] = ipcc_category
            row["Subcategory"] = ghg_category

        rows.append(row)

    return rows


def write_csv(rows: List[Dict[str, Any]], out_path: str) -> None:
    import csv

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Determine columns dynamically based on what's in the rows
    fieldnames = [
        "meta_id",
        "chapter",
        "table_id",
        "desc",
    ]
    # Add category columns if present
    if rows and "IPCC_Category" in rows[0]:
        fieldnames.append("IPCC_Category")
    if rows and "Subcategory" in rows[0]:
        fieldnames.append("Subcategory")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_yaml(rows: List[Dict[str, Any]], out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.explicit_start = False
    yaml.default_flow_style = False

    # Build a mapping keyed by meta_id to make it easy to reference
    meta_map: CommentedMap = CommentedMap()
    for r in rows:
        entry: CommentedMap = CommentedMap()
        entry["table_id"] = r["table_id"]
        entry["chapter"] = r["chapter"]
        if r.get("desc"):
            entry["desc"] = r["desc"]
        # Only include categories if they exist in the data
        if "Subcategory" in r:
            entry["subcategory"] = r.get("Subcategory", "")
        if "IPCC_Category" in r:
            entry["ipcc_category"] = r.get("IPCC_Category", "")
        meta_map[r["meta_id"]] = entry
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.dump(meta_map, f)


def _apply_label_map(rows: List[Dict[str, Any]], label_map_path: str) -> None:
    """Apply overrides from a CSV file with columns such as:
    - table_id,label
    or
    - meta_id,label
    The 'label' column value will replace the GHG source category.
    """
    import csv
    if not label_map_path or not os.path.exists(label_map_path):
        return
    with open(label_map_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        overrides_by_table = {}
        overrides_by_meta = {}
        for row in reader:
            label = (
                row.get("label")
                or row.get("Subcategory")
                or row.get("subcategory")
                or row.get("GHG source category")
                or row.get("ghg_source_category")
            )
            if not label:
                continue
            if row.get("table_id"):
                overrides_by_table[str(row["table_id"]).strip()] = label
            if row.get("meta_id"):
                overrides_by_meta[str(row["meta_id"]).strip()] = label
    for r in rows:
        if r["meta_id"] in overrides_by_meta:
            r["Subcategory"] = overrides_by_meta[r["meta_id"]]
        elif r["table_id"] in overrides_by_table:
            r["Subcategory"] = overrides_by_table[r["table_id"]]


def main(input_path: str = DEFAULT_INPUT,
         csv_out: str = CSV_OUT,
         yaml_out: str = YAML_OUT,
         label_map: str = "",
         extract_categories: bool = False) -> Dict[str, Any]:
    """
    Programmatic entry point for extracting EPA GHGI metadata.

    Parameters
    ----------
    input_path: str
        Path to the EPA_GHGI.yaml in the flowsa package (or a custom path)
    csv_out: str
        Output CSV file path for the flattened metadata table
    yaml_out: str
        Output YAML file path for the keyed metadata map
    label_map: str
        Optional CSV with custom label overrides (columns: table_id,label or meta_id,label)
    extract_categories: bool
        Whether to extract IPCC_Category and Subcategory fields (default: False)

    Returns
    -------
    dict
        Summary of the extraction including counts and output paths
    """
    rows = build_meta_rows(input_path, extract_categories=extract_categories)
    if extract_categories:
        _apply_label_map(rows, label_map)
    write_csv(rows, csv_out)
    write_yaml(rows, yaml_out)
    summary = {
        "records": len(rows),
        "csv": csv_out,
        "yaml": yaml_out,
        "label_map_used": bool(label_map),
        "categories_extracted": extract_categories,
    }
    print(f"Wrote {summary['records']} meta rows")
    print(f"CSV: {summary['csv']}")
    print(f"YAML: {summary['yaml']}")
    if extract_categories:
        print("  (with IPCC_Category and Subcategory)")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract MetaSource-like entries from EPA_GHGI.yaml")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to EPA_GHGI.yaml")
    parser.add_argument("--csv-out", default=CSV_OUT, help="CSV output path")
    parser.add_argument("--yaml-out", default=YAML_OUT, help="YAML output path")
    parser.add_argument("--label-map", default="", help="Optional CSV with per-table or per-meta custom labels")
    parser.add_argument(
        "--extract-categories",
        action="store_true",
        help="Extract IPCC_Category and Subcategory fields (legacy feature, disabled by default)"
    )
    args = parser.parse_args()

    # Delegate to the programmatic entry point
    main(
        input_path=args.input,
        csv_out=args.csv_out,
        yaml_out=args.yaml_out,
        label_map=args.label_map,
        extract_categories=args.extract_categories,
    )
