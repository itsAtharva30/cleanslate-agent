import cleanslate


def test_package_imports():
    assert cleanslate.__name__ == "cleanslate"


def test_version_looks_like_x_y_z():
    parts = cleanslate.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)