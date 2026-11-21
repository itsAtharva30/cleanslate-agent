import re
import subprocess
import sys

import pytest
from openpyxl import Workbook

import cleanslate.cli as cli_module
from cleanslate import __version__
from cleanslate.cli import main
from cleanslate.errors import OriginalModifiedError
from cleanslate.hashing import sha256_file


def make_workbook(path):
    wb = Workbook()
    main_sheet = wb.active
    main_sheet.title = "Main"
    main_sheet.append(["id", "qty", "total"])
    main_sheet.append(["007", 2, "=B2*10"])
    main_sheet.merge_cells("A4:B4")
    main_sheet["A4"] = "merged"
    hidden = wb.create_sheet("Hid")
    hidden.append([1])
    hidden.sheet_state = "hidden"
    wb.save(path)
    return path


@pytest.fixture
def source(tmp_path):
    folder = tmp_path / "src"
    folder.mkdir()
    return make_workbook(folder / "sales.xlsx")


@pytest.fixture
def runs(tmp_path):
    return tmp_path / "runs"


def run_cli(path, runs_dir):
    return main(["ingest", str(path), "--runs-dir", str(runs_dir)])


def test_success_prints_a_summary_and_returns_0(source, runs, capsys):
    assert run_cli(source, runs) == 0
    out = capsys.readouterr().out
    assert "Run folder:" in out
    assert "Manifest:" in out
    assert re.search(r"Sheets:\s+2", out)
    assert re.search(r"Original:\s+unchanged", out)
    assert re.search(r"Warnings:\s+3", out)


def test_success_writes_run_folder_and_manifest(source, runs):
    assert run_cli(source, runs) == 0
    run_dirs = list(runs.iterdir())
    assert len(run_dirs) == 1
    assert (run_dirs[0] / "manifest.json").is_file()
    assert (run_dirs[0] / "input" / "sales.xlsx").is_file()


def test_warnings_are_listed(source, runs, capsys):
    run_cli(source, runs)
    out = capsys.readouterr().out
    assert "Hidden sheet: 'Hid'" in out
    assert "Merged cells in 'Main'" in out
    assert "Formulas in 'Main'" in out


def test_output_never_contains_cell_contents(tmp_path, runs, capsys):
    wb = Workbook()
    wb.active.title = "Main"
    wb.active.append(["SECRET-123", "=1+1"])
    f = tmp_path / "s.xlsx"
    wb.save(f)
    assert run_cli(f, runs) == 0
    assert "SECRET" not in capsys.readouterr().out


def test_original_is_unchanged_by_the_cli(source, runs):
    before = sha256_file(source)
    run_cli(source, runs)
    assert sha256_file(source) == before


@pytest.mark.parametrize(
    ("name", "content"),
    [
        ("missing.xlsx", None),
        ("data.csv", b"a,b"),
        ("empty.xlsx", b""),
        ("fake.xlsx", b"not a workbook"),
    ],
)
def test_input_errors_exit_1_with_a_one_line_message(
    tmp_path, runs, capsys, name, content
):
    f = tmp_path / name
    if content is not None:
        f.write_bytes(content)
    assert run_cli(f, runs) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")
    assert len(captured.err.strip().splitlines()) == 1
    assert "Traceback" not in captured.err
    assert not runs.exists()


def test_integrity_errors_exit_3(tmp_path, runs, monkeypatch, capsys):
    def tampered(*args, **kwargs):
        raise OriginalModifiedError("the original changed")

    monkeypatch.setattr(cli_module, "ingest", tampered)
    assert run_cli(tmp_path / "x.xlsx", runs) == 3
    assert capsys.readouterr().err.startswith("error: ")


def test_unexpected_errors_are_not_swallowed(tmp_path, runs, monkeypatch):
    def buggy(*args, **kwargs):
        raise RuntimeError("bug")

    monkeypatch.setattr(cli_module, "ingest", buggy)
    with pytest.raises(RuntimeError, match="bug"):
        run_cli(tmp_path / "x.xlsx", runs)


def test_missing_command_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_missing_file_argument_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["ingest"])
    assert exc_info.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_version_flag_prints_the_version(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert f"cleanslate {__version__}" in capsys.readouterr().out


def test_default_runs_root_is_anchored_to_the_repo():
    root = cli_module.DEFAULT_RUNS_ROOT
    assert root.is_absolute()
    assert root.parts[-2:] == ("data", "runs")
    assert (root.parents[1] / "pyproject.toml").is_file()


def test_omitted_runs_dir_uses_the_default(source, tmp_path, monkeypatch):
    default = tmp_path / "default_runs"
    monkeypatch.setattr(cli_module, "DEFAULT_RUNS_ROOT", default)
    assert main(["ingest", str(source)]) == 0
    assert len(list(default.iterdir())) == 1


def test_python_dash_m_entry_point_works(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "cleanslate", "--version"],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        check=False,
    )
    assert result.returncode == 0
    assert f"cleanslate {__version__}" in result.stdout
