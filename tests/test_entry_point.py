import importlib
import tomllib
from importlib.metadata import entry_points
from pathlib import Path

from cleanslate.cli import main

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def test_console_script_is_declared_and_resolves_to_main():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    target = data["project"]["scripts"]["cleanslate"]
    module_name, function_name = target.split(":")
    function = getattr(importlib.import_module(module_name), function_name)
    assert function is main


def test_installed_metadata_exposes_the_command():
    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts.get("cleanslate") == "cleanslate.cli:main"
