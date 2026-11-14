import pandas as pd
from openpyxl import Workbook

from cleanslate.hashing import sha256_file
from cleanslate.ingest import read_workbook


def make_messy(path):
    wb = Workbook()
    main = wb.active
    main.title = "Main"
    main.append(["id", "qty", "total"])
    main.append(["007", 2, "=B2*10"])
    main.append([8, 3, "=B3*10"])
    main.merge_cells("A5:B5")
    main["A5"] = "merged"
    hidden = wb.create_sheet("Hid")
    hidden.append([1])
    hidden.sheet_state = "hidden"
    very = wb.create_sheet("VHid")
    very.append([2])
    very.sheet_state = "veryHidden"
    wb.save(path)
    return path


def make_clean(path):
    wb = Workbook()
    wb.active.title = "Clean"
    wb.active.append(["a", 1])
    wb.active.append(["b", 2])
    wb.save(path)
    return path


def test_reads_every_sheet_including_hidden_ones(tmp_path):
    data = read_workbook(make_messy(tmp_path / "m.xlsx"))
    assert list(data.sheets) == ["Main", "Hid", "VHid"]
    assert [i.name for i in data.sheet_infos] == ["Main", "Hid", "VHid"]


def test_values_are_raw_not_guessed(tmp_path):
    main = read_workbook(make_messy(tmp_path / "m.xlsx")).sheets["Main"]
    assert main.iloc[1, 0] == "007"
    assert main.iloc[2, 0] == 8
    assert main.iloc[1, 1] == 2


def test_first_row_is_data_not_a_header(tmp_path):
    main = read_workbook(make_messy(tmp_path / "m.xlsx")).sheets["Main"]
    assert main.iloc[0].tolist() == ["id", "qty", "total"]
    assert list(main.columns) == [0, 1, 2]


def test_formula_cells_are_counted_and_read_as_empty(tmp_path):
    data = read_workbook(make_messy(tmp_path / "m.xlsx"))
    assert data.sheet_infos[0].formula_cells == 2
    assert pd.isna(data.sheets["Main"].iloc[1, 2])


def test_merged_ranges_are_counted_and_only_top_left_has_a_value(tmp_path):
    data = read_workbook(make_messy(tmp_path / "m.xlsx"))
    assert data.sheet_infos[0].merged_ranges == 1
    main = data.sheets["Main"]
    assert main.iloc[4, 0] == "merged"
    assert pd.isna(main.iloc[4, 1])


def test_sheet_states_are_reported(tmp_path):
    data = read_workbook(make_messy(tmp_path / "m.xlsx"))
    assert [i.state for i in data.sheet_infos] == ["visible", "hidden", "veryHidden"]


def test_row_and_column_counts_match_the_frames(tmp_path):
    data = read_workbook(make_messy(tmp_path / "m.xlsx"))
    for info in data.sheet_infos:
        assert (info.n_rows, info.n_cols) == data.sheets[info.name].shape
    assert (data.sheet_infos[0].n_rows, data.sheet_infos[0].n_cols) == (5, 3)


def test_hazard_warnings_name_the_sheets(tmp_path):
    text = "\n".join(read_workbook(make_messy(tmp_path / "m.xlsx")).warnings)
    assert "Hidden sheet: 'Hid'" in text
    assert "Very hidden sheet: 'VHid'" in text
    assert "Merged cells in 'Main'" in text
    assert "Formulas in 'Main'" in text


def test_clean_workbook_has_no_warnings(tmp_path):
    data = read_workbook(make_clean(tmp_path / "c.xlsx"))
    assert data.warnings == []


def test_warnings_and_infos_never_contain_cell_contents(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Main"
    ws.append(["SECRET-123", "=1+1"])
    ws.merge_cells("C1:D1")
    ws["C1"] = "SECRET-456"
    wb.save(tmp_path / "s.xlsx")
    data = read_workbook(tmp_path / "s.xlsx")
    dumped = "\n".join(data.warnings) + repr(data.sheet_infos)
    assert "SECRET" not in dumped
    assert data.warnings  # hazards were found, so the check above means something


def test_reading_does_not_modify_the_file(tmp_path):
    f = make_messy(tmp_path / "m.xlsx")
    before = sha256_file(f)
    read_workbook(f)
    assert sha256_file(f) == before


def test_file_handle_is_released(tmp_path):
    f = make_messy(tmp_path / "m.xlsx")
    read_workbook(f)
    f.unlink()
    assert not f.exists()


def test_empty_sheet_has_zero_size(tmp_path):
    f = tmp_path / "e.xlsx"
    Workbook().save(f)
    info = read_workbook(f).sheet_infos[0]
    assert (info.n_rows, info.n_cols) == (0, 0)
