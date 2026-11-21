import importlib.util
import json
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import load_workbook

from cleanslate.hashing import sha256_file
from cleanslate.ingest import ingest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "make_messy_sample.py"


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("make_messy_sample", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(gen):
    return gen.generate(gen.DEFAULT_SEED)


@pytest.fixture(scope="module")
def sample(gen, tmp_path_factory):
    return gen.write_sample(tmp_path_factory.mktemp("sample"))


def by_kind(problems, kind):
    return [p for p in problems if p["kind"] == kind]


def test_same_seed_gives_identical_data(gen):
    assert gen.generate(5) == gen.generate(5)


def test_different_seed_gives_different_data(gen):
    assert gen.generate(5) != gen.generate(6)


def test_sizes_and_category_counts(generated):
    rows, problems = generated
    assert len(rows) == 210
    assert len(problems) == 60
    counts = {}
    for p in problems:
        counts[p["category"]] = counts.get(p["category"], 0) + 1
    assert counts == {"red": 14, "orange": 4, "yellow": 22, "blue": 10, "purple": 10}


def test_every_problem_points_inside_the_data(gen, generated):
    _, problems = generated
    first = gen.FIRST_DATA_ROW
    last = first + 209
    assert all(first <= p["row"] <= last for p in problems)


def test_no_row_carries_two_problems(generated):
    _, problems = generated
    hit = [p["row"] for p in problems]
    assert len(hit) == len(set(hit))


def test_red_problems_are_really_invalid(generated):
    _, problems = generated
    assert all(p["value"] < 0 for p in by_kind(problems, "negative_quantity"))
    assert all("@" not in p["value"] for p in by_kind(problems, "invalid_email"))
    dates = by_kind(problems, "impossible_date")
    assert len(dates) == 4
    for p in dates:
        with pytest.raises(ValueError):
            datetime.strptime(p["value"], "%Y-%m-%d")


def test_orange_outliers_are_far_above_normal_prices(generated):
    _, problems = generated
    outliers = by_kind(problems, "price_outlier")
    assert len(outliers) == 4
    assert all(p["value"] > 400 for p in outliers)


def test_yellow_problems_have_a_correct_expected_value(gen, generated):
    _, problems = generated
    for p in by_kind(problems, "messy_name"):
        assert " ".join(p["value"].split()).title() == p["expected"]
    for p in by_kind(problems, "date_format"):
        day, month, year = p["value"].split("/")
        assert f"{year}-{month}-{day}" == p["expected"]
        assert int(day) > 12
    aliases = {}
    for country, code in gen.COUNTRY_CODES.items():
        aliases[country.lower()] = country
        aliases[code.lower()] = country
    for p in by_kind(problems, "country_variant"):
        assert aliases[p["value"].strip().lower()] == p["expected"]


def test_blue_problems_blank_a_cell_but_keep_the_truth(generated):
    _, problems = generated
    blue = [p for p in problems if p["category"] == "blue"]
    assert len(blue) == 10
    assert all(p["value"] is None and p["expected"] is not None for p in blue)


def test_duplicates_copy_an_earlier_row(gen, generated):
    rows, problems = generated
    first = gen.FIRST_DATA_ROW
    exact = by_kind(problems, "exact_duplicate")
    near = by_kind(problems, "near_duplicate")
    assert (len(exact), len(near)) == (6, 4)
    for p in exact:
        copy = rows[p["row"] - first]
        original = rows[p["duplicate_of"] - first]
        assert copy == original
        assert p["duplicate_of"] < p["row"]
    for p in near:
        copy = rows[p["row"] - first]
        original = rows[p["duplicate_of"] - first]
        assert copy[0] == original[0]
        assert copy[1] != original[1]
        assert copy[1].strip().lower() == original[1].lower()


def test_ground_truth_matches_the_workbook_cells(sample):
    xlsx, truth = sample
    document = json.loads(truth.read_text(encoding="utf-8"))
    wb = load_workbook(xlsx)
    try:
        ws = wb[document["sheet"]]
        checked = 0
        for p in document["problems"]:
            if p["column"] is None:
                continue
            assert ws[f"{p['column']}{p['row']}"].value == p["value"]
            checked += 1
    finally:
        wb.close()
    assert checked == 50


def test_structural_hazards_are_present(sample):
    xlsx, truth = sample
    document = json.loads(truth.read_text(encoding="utf-8"))
    hazards = document["structural_hazards"]
    wb = load_workbook(xlsx)
    try:
        orders = wb["Orders"]
        assert [str(r) for r in orders.merged_cells.ranges] == [
            hazards["merged_title_range"]
        ]
        assert orders["A3"].value == "order_id"
        assert orders["A4"].value == "0001"
        assert wb["Lookup"].sheet_state == "hidden"
        formulas = [
            cell
            for row in wb["Summary"].iter_rows()
            for cell in row
            if cell.data_type == "f"
        ]
        assert len(formulas) == hazards["formula_cells"]["Summary"]
    finally:
        wb.close()


def test_truth_file_is_byte_identical_for_the_same_seed(gen, tmp_path):
    _, first = gen.write_sample(tmp_path / "a", seed=3)
    _, second = gen.write_sample(tmp_path / "b", seed=3)
    assert sha256_file(first) == sha256_file(second)


def test_different_seeds_give_different_truth_files(gen, tmp_path):
    _, first = gen.write_sample(tmp_path / "a", seed=3)
    _, second = gen.write_sample(tmp_path / "b", seed=4)
    assert sha256_file(first) != sha256_file(second)


def test_command_line_entry_point_writes_both_files(gen, tmp_path, capsys):
    assert gen.main(["--out", str(tmp_path / "cli"), "--seed", "7"]) == 0
    assert "Wrote" in capsys.readouterr().out
    assert (tmp_path / "cli" / gen.XLSX_NAME).is_file()
    assert (tmp_path / "cli" / gen.TRUTH_NAME).is_file()


def test_default_output_folder_is_inside_the_repo_data_folder(gen):
    assert gen.DEFAULT_OUT.is_absolute()
    assert gen.DEFAULT_OUT.parts[-2:] == ("data", "samples")


def test_ingest_handles_the_sample(sample, tmp_path):
    xlsx, _ = sample
    before = sha256_file(xlsx)
    result = ingest(xlsx, tmp_path / "runs")
    m = result.manifest
    assert [s.name for s in m.sheets] == ["Orders", "Summary", "Lookup"]
    orders = m.sheets[0]
    assert (orders.n_rows, orders.n_cols, orders.merged_ranges) == (213, 7, 1)
    assert m.sheets[1].formula_cells == 2
    assert m.sheets[2].state == "hidden"
    text = "\n".join(m.warnings)
    assert "Hidden sheet: 'Lookup'" in text
    assert "Merged cells in 'Orders'" in text
    assert "Formulas in 'Summary'" in text
    assert m.original_sha256 == m.copy_sha256 == m.original_sha256_after == before
    assert sha256_file(xlsx) == before
    assert result.sheets["Orders"].iloc[3, 0] == "0001"
