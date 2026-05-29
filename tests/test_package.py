"""Smoke tests for package structure and metadata (PKG-02, PKG-03, PKG-05)."""
import tarfile
import pathlib
import zipfile

import pytest


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
    assert 'dynamic = ["version"]' in content, "Missing dynamic version declaration"
    assert 'requires-python = ">=3.10"' in content, "Missing Python version requirement"
    assert '"numpy>=1.24"' in content, "Missing numpy dependency"
    assert '"scikit-learn>=1.3"' in content, "Missing scikit-learn dependency"
    assert '"typing-extensions>=4.8"' in content, "Missing typing-extensions dependency"
    assert 'build-backend = "hatchling.build"' in content, "Missing hatchling build backend"
    assert "[tool.hatch.version]" in content, "Missing hatch version table"
    assert 'path = "corpulse/__init__.py"' in content, "Missing hatch version path"
    assert 'version = "0.1.0"' not in content, "Static version should not be declared in pyproject"


def test_qdrant_extra_declared():
    """PKG-03: Optional [qdrant] extra declares qdrant-client."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "[project.optional-dependencies]" in content, "Missing optional-dependencies section"
    assert "qdrant-client" in content, "Missing qdrant-client in optional dependencies"


def test_postgres_extra_declared():
    """INT-02: Optional [postgres] extra declares psycopg."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'postgres = ["psycopg[binary,pool]>=3.2"]' in content, "Missing binary-safe postgres extra"


def test_postgres_async_extra_declared():
    """INT-02: Optional [postgres-async] extra declares asyncpg."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "postgres-async" in content and "asyncpg" in content, (
        "Missing asyncpg postgres-async extra"
    )


def test_hatchling_packages_explicit():
    """Hatchling explicitly declares corpulse as the only package."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'packages = ["corpulse"]' in content, "Missing explicit hatchling packages declaration"


def test_sdist_include_configuration():
    """PKG-03: sdist includes the package, README, license, and pyproject."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "[tool.hatch.build.targets.sdist]" in content, "Missing sdist target configuration"
    assert 'include = [' in content, "Missing sdist include list"
    assert '"/corpulse"' in content, "Missing corpulse sdist include"
    assert '"/README.md"' in content, "Missing README sdist include"
    assert '"/LICENSE"' in content, "Missing LICENSE sdist include"
    assert '"/pyproject.toml"' in content, "Missing pyproject sdist include"


def test_dynamic_version_configured():
    """PKG-01: Version is sourced dynamically from corpulse/__init__.py."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'dynamic = ["version"]' in content
    assert "[tool.hatch.version]" in content
    assert 'path = "corpulse/__init__.py"' in content
    assert 'version = "0.1.0"' not in content


def test_pypi_metadata_declared():
    """PKG-01: PyPI metadata is declared for discoverability."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'authors = [{ name = "Arkady B" }]' in content
    assert '"rag"' in content
    assert '"retrieval-augmented-generation"' in content
    assert '"vector-database"' in content
    assert '"corpus-health"' in content
    assert '"observability"' in content
    assert 'Development Status :: 3 - Alpha' in content
    assert 'Intended Audience :: Developers' in content
    assert 'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)' in content
    assert 'Programming Language :: Python :: 3.10' in content
    assert 'Programming Language :: Python :: 3.11' in content
    assert 'Programming Language :: Python :: 3.12' in content
    assert 'Topic :: Software Development :: Libraries :: Python Modules' in content
    assert 'Topic :: Scientific/Engineering :: Artificial Intelligence' in content
    assert 'Homepage = "https://github.com/arkadyb/corpulse"' in content
    assert 'Repository = "https://github.com/arkadyb/corpulse"' in content
    assert 'Source = "https://github.com/arkadyb/corpulse"' in content
    assert 'Issues = "https://github.com/arkadyb/corpulse/issues"' in content


def test_distribution_install_tests_are_gated():
    """Phase 34 install tests are opt-in through CORPULSE_RUN_INSTALL_TESTS."""
    install_tests = pathlib.Path(__file__).resolve().parent / "test_distribution_installs.py"
    content = install_tests.read_text()
    assert "CORPULSE_RUN_INSTALL_TESTS=1" in content
    assert "pytest.mark.skipif" in content


def test_optional_extras_declared_for_install_matrix():
    """EXTRA-01/04: pyproject declares every optional extra in the install matrix."""
    pyproject = pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert 'qdrant = ["qdrant-client>=1.7"]' in content
    assert 'postgres = ["psycopg[binary,pool]>=3.2"]' in content
    assert 'postgres-async = ["asyncpg>=0.29"]' in content
    assert 'fastapi = ["fastapi>=0.110.0", "pydantic>=2.0.0"]' in content


def test_optional_dependency_guidance_is_actionable():
    """EXTRA-03: optional dependency failures tell users exactly what to install."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    files = [
        repo_root / "corpulse" / "integrations" / "qdrant.py",
        repo_root / "corpulse" / "backends" / "postgres.py",
        repo_root / "corpulse" / "backends" / "postgres_async.py",
        repo_root / "corpulse" / "fastapi.py",
        repo_root / "corpulse" / "core.py",
        repo_root / "corpulse" / "async_core.py",
    ]
    content = "\n".join(path.read_text() for path in files)
    assert "pip install corpulse[qdrant]" in content
    assert "pip install corpulse[postgres]" in content
    assert "pip install corpulse[postgres-async]" in content
    assert "pip install corpulse[fastapi]" in content
    assert "pip install pandas to use to_dataframe()" in content


def test_readme_uses_pypi_install_commands():
    """DOC-01: README points users at PyPI-first install commands."""
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    readme = repo_root / "README.md"
    pyproject = repo_root / "pyproject.toml"

    readme_content = readme.read_text()
    pyproject_content = pyproject.read_text()

    assert "pip install corpulse" in readme_content
    assert 'pip install "corpulse[qdrant]"' in readme_content
    assert 'pip install "git+https://github.com/arkadyb/corpulse.git"' in readme_content
    assert ".github/RELEASE_CHECKLIST.md" in readme_content
    assert "not yet on PyPI" not in readme_content
    assert "corpulse[qdrant] @ git+https://github.com/arkadyb/corpulse.git" not in readme_content
    assert 'readme = "README.md"' in pyproject_content


def test_built_artifacts_include_expected_files():
    """PKG-03: built artifacts contain the expected release files."""
    dist_dir = pathlib.Path(__file__).resolve().parent.parent / "dist"
    sdists = list(dist_dir.glob("*.tar.gz"))
    wheels = list(dist_dir.glob("*.whl"))

    if not sdists and not wheels:
        pytest.skip("No built artifacts found")

    if sdists:
        newest_sdist = max(sdists, key=lambda path: path.stat().st_mtime)
        with tarfile.open(newest_sdist, "r:gz") as archive:
            names = archive.getnames()
        assert any(name.endswith("pyproject.toml") for name in names), "sdist missing pyproject.toml"
        assert any(name.endswith("README.md") for name in names), "sdist missing README.md"
        assert any(name.endswith("LICENSE") for name in names), "sdist missing LICENSE"
        assert any(name.endswith("corpulse/__init__.py") for name in names), (
            "sdist missing corpulse/__init__.py"
        )

    if wheels:
        newest_wheel = max(wheels, key=lambda path: path.stat().st_mtime)
        with zipfile.ZipFile(newest_wheel) as archive:
            names = archive.namelist()
        assert any(name.endswith("corpulse/__init__.py") for name in names), (
            "wheel missing corpulse/__init__.py"
        )
        assert any(name.endswith(".dist-info/METADATA") for name in names), (
            "wheel missing dist-info/METADATA"
        )
