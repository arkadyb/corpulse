"""Isolated install verification for built wheel artifacts."""
import importlib.util
import os
import pathlib
import subprocess
import sys
import textwrap
import venv

import pytest

RUN_INSTALL_TESTS = os.environ.get("CORPULSE_RUN_INSTALL_TESTS") == "1"
pytestmark = pytest.mark.skipif(
    not RUN_INSTALL_TESTS,
    reason="set CORPULSE_RUN_INSTALL_TESTS=1 to run isolated install tests",
)


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parent


def _latest_wheel() -> pathlib.Path:
    dist_dir = _repo_root() / "dist"
    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        pytest.skip("No built wheel found; run python -m build first")
    return max(wheels, key=lambda path: path.stat().st_mtime)


def _create_venv(tmp_path: pathlib.Path) -> pathlib.Path:
    venv_dir = tmp_path / "venv"
    builder = venv.EnvBuilder(with_pip=True, clear=True)
    builder.create(venv_dir)
    return venv_dir


def _python(venv_dir: pathlib.Path) -> pathlib.Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(py: pathlib.Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(py), *args],
        check=True,
        text=True,
        capture_output=True,
    )


def _install_wheel(py: pathlib.Path, wheel: pathlib.Path, extra: str | None = None) -> None:
    if extra is None:
        requirement = str(wheel)
    else:
        requirement = f"corpulse[{extra}] @ {wheel.resolve().as_uri()}"
    _run(py, ["-m", "pip", "install", requirement])


def test_distribution_install_tests_are_gated():
    content = (_repo_root() / "tests" / "test_distribution_installs.py").read_text()
    assert "CORPULSE_RUN_INSTALL_TESTS=1" in content
    assert "pytest.mark.skipif" in content


def test_base_wheel_install_imports_without_optional_dependencies(tmp_path):
    wheel = _latest_wheel()
    venv_dir = _create_venv(tmp_path)
    py = _python(venv_dir)

    _install_wheel(py, wheel)

    snippet = textwrap.dedent(
        """
        import importlib.util

        import corpulse
        from corpulse import Corpulse

        assert corpulse.__version__ == "0.1.0"
        assert callable(Corpulse)

        for name in [
            "qdrant_client",
            "psycopg",
            "asyncpg",
            "fastapi",
            "pandas",
            "tabulate",
        ]:
            assert importlib.util.find_spec(name) is None, (
                f"{name} should not be installed by the base extra-free wheel"
            )
        """
    )

    _run(py, ["-c", snippet])
