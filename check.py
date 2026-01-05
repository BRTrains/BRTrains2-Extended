import re
from pathlib import Path
from argparse import ArgumentParser
import pandas as pd

PNML_DIR = Path("src")
CSV_FILE = Path("build/BRTrains XL Tracking Spreadsheet - Sheet1.csv")
BACKUP_DIR = Path("template/autogen/backup")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

CSV_ITEM_ID_COL = "Unit ID"

CSV_FIELD_MAP = {
    "Cost Factor": "cost_factor",
    "Running Cost Factor": "running_cost_factor",
    "Air Drag Coefficient": "air_drag_coefficient",
    "Tractive Effort Coefficient": "tractive_effort_coefficient",
}

FIELDS_MAX = {
    "cost_factor",
    "running_cost_factor",
    "tractive_effort_coefficient",
}

FIELDS_MIN = {
    "air_drag_coefficient",
}

ALL_FIELDS = FIELDS_MAX | FIELDS_MIN

def load_csv_aggregates(csv_path):
    df = pd.read_csv(csv_path,
                     dtype={
                         "Unit ID": str,
                         "Cost Factor": int,
                         "Running Cost Factor": int
                    },
                    keep_default_na=False)
    df["Unit ID"] = df["Unit ID"].str.strip()

    # Keep only required columns
    required_cols = [CSV_ITEM_ID_COL] + list(CSV_FIELD_MAP.keys())
    df = df[required_cols]

    # Drop rows without Unit ID
    df = df.dropna(subset=[CSV_ITEM_ID_COL])

    # Convert numeric columns
    for col in CSV_FIELD_MAP:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    aggregates = {}

    for item_id, group in df.groupby(CSV_ITEM_ID_COL):
        agg = {}

        for csv_col, internal_key in CSV_FIELD_MAP.items():
            series = group[csv_col].dropna()
            if series.empty:
                continue

            if internal_key in FIELDS_MAX:
                agg[internal_key] = series.max()
            else:
                agg[internal_key] = series.min()

        aggregates[str(item_id)] = agg

    return aggregates


ITEM_DECL_RE = re.compile(
    r"item\s*\(\s*FEAT_TRAINS\s*,\s*[^,]+\s*,\s*(\d+)\s*\)"
)

FIELD_RE = re.compile(
    r"^(?P<indent>\s*)(?P<field>cost_factor|running_cost_factor|air_drag_coefficient|tractive_effort_coefficient)"
    r"\s*:(?P<spacing>\s*)(?P<value>[-+]?\d*\.?\d+)\s*;",
    re.MULTILINE
)


def parse_pnml_file(path):
    """
    Returns:
        dict with keys:
            item_id
            values (dict[field] -> float)
    """
    text = path.read_text(encoding="utf-8")

    item_match = ITEM_DECL_RE.search(text)
    if not item_match:
        return None

    item_id = item_match.group(1)

    values = {}
    for field, value in FIELD_RE.findall(text):
        values[field] = float(value)

    return {
        "item_id": item_id,
        "values": values,
    }


def process_pnml_file(path, csv_aggregates, do_check, do_overwrite):
    text = path.read_text(encoding="utf-8")

    item_match = ITEM_DECL_RE.search(text)
    if not item_match:
        return

    item_id = item_match.group(1)
    if item_id not in csv_aggregates:
        print(f"[WARN] {path.name}: item_id {item_id} not found in CSV")
        return

    csv_values = csv_aggregates[item_id]

    matches = list(FIELD_RE.finditer(text))
    if not matches:
        return

    max_field_len = max(len(m.group("field")) for m in matches)
    updated = False

    def replacer(match):
        nonlocal updated

        indent = match.group("indent")
        field = match.group("field")
        spacing = match.group("spacing")
        old_value = float(match.group("value"))

        if field not in csv_values:
            return match.group(0)

        new_value = csv_values[field]

        if (new_value > 32767):
            new_value = 32767

        if do_check and old_value != new_value:
            print(
                f"[MISMATCH] {path.name} | {item_id} | {field}: "
                f"PNML={old_value}, CSV={new_value}"
            )

        if do_overwrite and old_value != new_value:
            updated = True
            return f"{indent}{field}:{spacing}{new_value};"

        return match.group(0)

    new_text = FIELD_RE.sub(replacer, text)

    if do_overwrite and updated:
        backup_path = BACKUP_DIR / path.name
        if not backup_path.exists():
            backup_path.write_text(text, encoding="utf-8")

        path.write_text(new_text, encoding="utf-8")
        print(f"[UPDATED] {path.name}")


def main(print_check, overwrite):
    csv_aggregates = load_csv_aggregates(CSV_FILE)

    for pnml_path in PNML_DIR.rglob("*.pnml"):
        process_pnml_file(
            pnml_path,
            csv_aggregates,
            do_check=print_check,
            do_overwrite=overwrite,
        )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Report mismatches")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite PNML values")
    args = parser.parse_args()

    main(args.check, args.overwrite)

