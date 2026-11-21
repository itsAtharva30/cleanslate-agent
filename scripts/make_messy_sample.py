"""Generate a messy sample workbook plus a ground-truth file of planted problems.

Run it from anywhere:
    python scripts/make_messy_sample.py
    python scripts/make_messy_sample.py --out some/folder --seed 7

The DATA is repeatable for a given seed. The .xlsx BYTES are not: openpyxl stamps
the save time into the file properties and zip stamps each entry, so never compare
file hashes of generated workbooks. The ground-truth JSON holds no timestamps, so
its bytes are repeatable.
"""

import argparse
import json
import random
import string
from pathlib import Path

from openpyxl import Workbook

DEFAULT_SEED = 42
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "data" / "samples"
XLSX_NAME = "messy_orders.xlsx"
TRUTH_NAME = "messy_orders.truth.json"

SHEET_ORDERS = "Orders"
SHEET_SUMMARY = "Summary"
SHEET_LOOKUP = "Lookup"
COLUMNS = [
    "order_id",
    "customer",
    "email",
    "country",
    "order_date",
    "quantity",
    "unit_price",
]
IX = {name: i for i, name in enumerate(COLUMNS)}
HEADER_ROW = 3
FIRST_DATA_ROW = 4
N_BASE_ROWS = 200

FIRST_NAMES = ["Alice", "Bruno", "Chen", "Dara", "Elif", "Farid", "Grace", "Hana"]
LAST_NAMES = ["Smith", "Rossi", "Wang", "Okafor", "Kaya", "Haddad", "Lopez", "Sato"]
COUNTRY_CODES = {
    "India": "IN",
    "United States": "US",
    "Germany": "DE",
    "Brazil": "BR",
    "Japan": "JP",
}

# (kind, legend category, how many rows). Each base row gets at most one problem.
# For the two duplicate kinds, the picked rows are the SOURCE rows that get copied.
PLAN = [
    ("negative_quantity", "red", 5),
    ("invalid_email", "red", 5),
    ("impossible_date", "red", 4),
    ("price_outlier", "orange", 4),
    ("messy_name", "yellow", 8),
    ("date_format", "yellow", 6),
    ("country_variant", "yellow", 8),
    ("missing_quantity", "blue", 5),
    ("missing_country", "blue", 5),
    ("exact_duplicate", "purple", 6),
    ("near_duplicate", "purple", 4),
]


def column_letter(name: str) -> str:
    return string.ascii_uppercase[IX[name]]


def generate(seed: int = DEFAULT_SEED) -> tuple[list[list], list[dict]]:
    """Return (rows, problems): the data rows and the ground truth for each problem.

    Rows in the ground truth are real Excel row numbers (data starts at row 4).
    """
    rng = random.Random(seed)
    countries = list(COUNTRY_CODES)

    rows: list[list] = []
    for i in range(N_BASE_ROWS):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        rows.append(
            [
                f"{i + 1:04d}",
                f"{first} {last}",
                f"{first.lower()}.{last.lower()}{i + 1}@example.com",
                rng.choice(countries),
                f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                rng.randint(1, 20),
                round(rng.uniform(5, 120), 2),
            ]
        )

    problems: list[dict] = []

    def record(
        row_index: int,
        column: str | None,
        category: str,
        kind: str,
        value,
        expected=None,
        duplicate_of: int | None = None,
        note: str = "",
    ) -> None:
        problems.append(
            {
                "sheet": SHEET_ORDERS,
                "row": FIRST_DATA_ROW + row_index,
                "column": None if column is None else column_letter(column),
                "column_name": column,
                "category": category,
                "kind": kind,
                "value": value,
                "expected": expected,
                "duplicate_of": duplicate_of,
                "note": note,
            }
        )

    # One sample, no repeats: every picked row gets exactly one kind of problem.
    chosen = rng.sample(range(N_BASE_ROWS), sum(count for _, _, count in PLAN))
    picks: dict[str, list[int]] = {}
    start = 0
    for kind, _category, count in PLAN:
        picks[kind] = chosen[start : start + count]
        start += count

    # Red: invalid or impossible, to be left unfixed.
    for i in picks["negative_quantity"]:
        row = rows[i]
        row[IX["quantity"]] = -rng.randint(1, 9)
        record(i, "quantity", "red", "negative_quantity", row[IX["quantity"]])

    for i in picks["invalid_email"]:
        row = rows[i]
        row[IX["email"]] = row[IX["email"]].replace("@", "")
        record(i, "email", "red", "invalid_email", row[IX["email"]])

    for i in picks["impossible_date"]:
        row = rows[i]
        row[IX["order_date"]] = rng.choice(
            ["2026-13-45", "2026-02-30", "2026-00-10", "2026-07-45"]
        )
        record(i, "order_date", "red", "impossible_date", row[IX["order_date"]])

    # Orange: outlier, to be kept.
    for i in picks["price_outlier"]:
        row = rows[i]
        row[IX["unit_price"]] = round(row[IX["unit_price"]] * 100, 2)
        record(
            i,
            "unit_price",
            "orange",
            "price_outlier",
            row[IX["unit_price"]],
            note="about 100x a typical price; extreme but possible, so keep it",
        )

    # Yellow: format problems with one obvious correct form.
    for i in picks["messy_name"]:
        row = rows[i]
        clean = row[IX["customer"]]
        first, last = clean.split()
        row[IX["customer"]] = f"  {first.upper()}   {last.lower()} "
        record(
            i,
            "customer",
            "yellow",
            "messy_name",
            row[IX["customer"]],
            expected=clean,
            note="case and spacing",
        )

    for i in picks["date_format"]:
        row = rows[i]
        month = rng.randint(1, 12)
        day = rng.randint(13, 28)  # above 12, so day-first is unambiguous
        row[IX["order_date"]] = f"{day:02d}/{month:02d}/2026"
        record(
            i,
            "order_date",
            "yellow",
            "date_format",
            row[IX["order_date"]],
            expected=f"2026-{month:02d}-{day:02d}",
            note="day-first format instead of ISO",
        )

    for i in picks["country_variant"]:
        row = rows[i]
        canonical = row[IX["country"]]
        row[IX["country"]] = rng.choice(
            [canonical.lower(), COUNTRY_CODES[canonical], canonical + " "]
        )
        record(
            i,
            "country",
            "yellow",
            "country_variant",
            row[IX["country"]],
            expected=canonical,
            note="lower case, ISO code or trailing space",
        )

    # Blue: missing, to be imputed. The removed true value is kept for scoring.
    for i in picks["missing_quantity"]:
        row = rows[i]
        true_value = row[IX["quantity"]]
        row[IX["quantity"]] = None
        record(
            i,
            "quantity",
            "blue",
            "missing_quantity",
            None,
            expected=true_value,
            note="true value removed; an imputation should land near it",
        )

    for i in picks["missing_country"]:
        row = rows[i]
        true_value = row[IX["country"]]
        row[IX["country"]] = None
        record(
            i,
            "country",
            "blue",
            "missing_country",
            None,
            expected=true_value,
            note="true value removed",
        )

    # Purple: duplicates are appended after the base rows, copied from clean rows.
    n_base = len(rows)
    for j, source in enumerate(picks["exact_duplicate"]):
        rows.append(list(rows[source]))
        record(
            n_base + j,
            None,
            "purple",
            "exact_duplicate",
            None,
            duplicate_of=FIRST_DATA_ROW + source,
            note="every field identical to the duplicate_of row",
        )

    offset = len(rows)
    for j, source in enumerate(picks["near_duplicate"]):
        row = list(rows[source])
        row[IX["customer"]] = row[IX["customer"]].upper() + " "
        rows.append(row)
        record(
            offset + j,
            None,
            "purple",
            "near_duplicate",
            None,
            duplicate_of=FIRST_DATA_ROW + source,
            note="same order_id; customer differs in case and a trailing space",
        )

    problems.sort(key=lambda p: (p["row"], p["column"] or ""))
    return rows, problems


def build_workbook(rows: list[list]) -> Workbook:
    wb = Workbook()

    orders = wb.active
    orders.title = SHEET_ORDERS
    orders["A1"] = "Q4 Orders Export"
    orders.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(COLUMNS))
    for c, name in enumerate(COLUMNS, start=1):
        orders.cell(row=HEADER_ROW, column=c, value=name)
    for r, row in enumerate(rows, start=FIRST_DATA_ROW):
        for c, value in enumerate(row, start=1):
            orders.cell(row=r, column=c, value=value)
    last_row = FIRST_DATA_ROW + len(rows) - 1

    summary = wb.create_sheet(SHEET_SUMMARY)
    summary["A1"] = "Metric"
    summary["B1"] = "Value"
    summary["A2"] = "Order rows"
    summary["B2"] = f"=COUNTA(Orders!A{FIRST_DATA_ROW}:A{last_row})"
    qty = column_letter("quantity")
    summary["A3"] = "Total quantity"
    summary["B3"] = f"=SUM(Orders!{qty}{FIRST_DATA_ROW}:{qty}{last_row})"

    lookup = wb.create_sheet(SHEET_LOOKUP)
    lookup.append(["country", "code"])
    for country, code in COUNTRY_CODES.items():
        lookup.append([country, code])
    lookup.sheet_state = "hidden"
    return wb


def build_truth_document(seed: int, rows: list[list], problems: list[dict]) -> dict:
    by_category: dict[str, int] = {}
    for problem in problems:
        by_category[problem["category"]] = by_category.get(problem["category"], 0) + 1
    last_col = string.ascii_uppercase[len(COLUMNS) - 1]
    return {
        "schema_version": 1,
        "seed": seed,
        "file": XLSX_NAME,
        "sheet": SHEET_ORDERS,
        "header_row": HEADER_ROW,
        "first_data_row": FIRST_DATA_ROW,
        "n_data_rows": len(rows),
        "columns": COLUMNS,
        "structural_hazards": {
            "merged_title_range": f"A1:{last_col}1",
            "hidden_sheets": [SHEET_LOOKUP],
            "formula_cells": {SHEET_SUMMARY: 2},
            "zero_padded_ids": "order_id holds text like 0001, not numbers",
        },
        "problem_counts_by_category": by_category,
        "problems": problems,
    }


def write_sample(
    out_dir: str | Path = DEFAULT_OUT, seed: int = DEFAULT_SEED
) -> tuple[Path, Path]:
    """Write the sample workbook and its ground-truth JSON; return both paths.

    Overwrites its own previous outputs in out_dir. That is fine here: these are
    generated files, not a user's original data.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, problems = generate(seed)

    xlsx_path = out_dir / XLSX_NAME
    build_workbook(rows).save(xlsx_path)

    truth_path = out_dir / TRUTH_NAME
    document = build_truth_document(seed, rows, problems)
    truth_path.write_text(
        json.dumps(document, indent=2), encoding="utf-8", newline="\n"
    )
    return xlsx_path, truth_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the messy sample workbook.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="random seed")
    args = parser.parse_args(argv)
    xlsx_path, truth_path = write_sample(args.out, args.seed)
    print(f"Wrote {xlsx_path}")
    print(f"Wrote {truth_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
