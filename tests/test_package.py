"""Smoke tests for package structure and metadata (PKG-02, PKG-03, PKG-05)."""
import pathlib


def test_package_structure():
    """PKG-05: Source files live under corpulse/ directory."""
    pkg_dir = pathlib.Path(__file__).resolve().parent.parent / "corpulse"
    assert pkg_dir.is_dir(), f"corpulse/ directory not found at {pkg_dir}"
    assert (pkg_dir / "__init__.py").is_file(), "corpulse/__init__.py missing"
    assert (pkg_dir / "db.py").is_file(), "corpulse/db.py missing"
    assert (pkg_dir / "core.py").is_file(), "corpulse/core.py missing"


def test_pyproject_metadata():
    """PKG-02: pyproject.toml has required build metadata."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    assert pyproject.is_file(), "pyproject.toml not found"
    content = pyproject.read_text()
    assert 'name = "corpulse"' in content, "Missing project name"
    assert 'requires-python = ">=3.10"' in content, "Missing Python version requirement"
    assert '"numpy>=1.24"' in content, "Missing numpy dependency"
    assert '"scikit-learn>=1.3"' in content, "Missing scikit-learn dependency"
    assert 'build-backend = "hatchling.build"' in content, "Missing hatchling build backend"


def test_qdrant_extra_declared():
    """PKG-03: Optional [qdrant] extra declares qdrant-client."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "[project.optional-dependencies]" in content, "Missing optional-dependencies section"
    assert "qdrant-client" in content, "Missing qdrant-client in optional dependencies"


def test_hatchling_packages_explicit():
    """Hatchling explicitly declares corpulse as the only package."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'packages = ["corpulse"]' in content, "Missing explicit hatchling packages declaration"
