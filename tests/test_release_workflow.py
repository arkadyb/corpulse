from __future__ import annotations

import pathlib


WORKFLOW = pathlib.Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"
TRUSTED_PUBLISHING = pathlib.Path(__file__).resolve().parent.parent / ".github" / "TRUSTED_PUBLISHING.md"
RELEASE_CHECKLIST = pathlib.Path(__file__).resolve().parent.parent / ".github" / "RELEASE_CHECKLIST.md"


def _workflow_text() -> str:
    return WORKFLOW.read_text()


def _build_job_text() -> str:
    content = _workflow_text()
    for marker in ("publish-testpypi:", "publish-pypi:"):
        if marker in content:
            return content.split(marker, 1)[0]
    return content


def _release_checklist_text() -> str:
    return RELEASE_CHECKLIST.read_text()


def test_release_workflow_builds_and_uploads_artifacts():
    content = _workflow_text()

    assert "name: Release" in content
    assert "workflow_dispatch:" in content
    assert "tags:" in content
    assert '"v*"' in content
    assert "python -m pytest" in content
    assert "python -m build" in content
    assert "actions/upload-artifact@v4" in content
    assert "python-package-distributions" in content
    assert "dist/*" in content


def test_build_job_does_not_request_oidc_publish_permission():
    content = _build_job_text()
    assert "id-token: write" not in content


def test_testpypi_publish_uses_trusted_publishing():
    content = _workflow_text()

    assert "publish-testpypi:" in content
    assert "if: github.event_name == 'workflow_dispatch'" in content
    assert "environment: testpypi" in content
    assert "id-token: write" in content
    assert "actions/download-artifact@v4" in content
    assert "pypa/gh-action-pypi-publish@release/v1" in content
    assert "repository-url: https://test.pypi.org/legacy/" in content


def test_release_workflow_does_not_use_long_lived_pypi_tokens():
    content = _workflow_text()
    for marker in [
        "password:",
        "username:",
        "api-token",
        "PYPI_API_TOKEN",
        "TEST_PYPI_API_TOKEN",
        "__token__",
    ]:
        assert marker not in content


def test_trusted_publishing_setup_documents_testpypi_values():
    content = TRUSTED_PUBLISHING.read_text()
    assert "owner: arkadyb" in content
    assert "repository: corpulse" in content
    assert "workflow: release.yml" in content
    assert "environment: testpypi" in content
    assert "RELEASE_CHECKLIST.md" in content


def test_pypi_publish_is_tag_gated_and_environment_gated():
    content = _workflow_text()

    assert "publish-pypi:" in content
    assert "if: startsWith(github.ref, 'refs/tags/v')" in content
    assert "environment: pypi" in content
    assert "id-token: write" in content
    assert "actions/download-artifact@v4" in content
    assert "pypa/gh-action-pypi-publish@release/v1" in content

    pypi_block = content.split("publish-pypi:", 1)[1]
    assert "repository-url:" not in pypi_block


def test_trusted_publishing_setup_documents_pypi_gate():
    content = TRUSTED_PUBLISHING.read_text()
    assert "environment: pypi" in content
    assert "required reviewers or an equivalent explicit approval gate" in content
    assert "Production PyPI publishing runs only from tags that match v*." in content
    assert "startsWith(github.ref, 'refs/tags/v')" in content


def test_release_checklist_covers_first_release_flow():
    content = _release_checklist_text()

    assert "First Release Checklist" in content
    assert "Version bump" in content
    assert "Build artifacts" in content
    assert "TestPyPI publish" in content
    assert "TestPyPI validation" in content
    assert "Production PyPI publish" in content
    assert "Post-publish PyPI validation for VAL-01" in content
    assert "Post-publish PyPI validation for VAL-02" in content
    assert "workflow_dispatch" in content
    assert "python -m build" in content
    assert "git tag v" in content
    assert "git push origin v" in content
    assert (
        "python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url "
        "https://pypi.org/simple/ corpulse"
    ) in content
    assert "python -m pip install corpulse" in content
    assert 'python -m pip install "corpulse[qdrant]"' in content
    assert "required reviewers or an equivalent explicit approval gate" in content


def test_release_checklist_uses_trusted_publishing_not_tokens():
    content = _release_checklist_text()

    assert "Do not create or use a PyPI API token for this workflow." in content
    assert "Do not store PYPI_API_TOKEN, TEST_PYPI_API_TOKEN, or any PyPI password secret for this workflow." in content
    for marker in [
        "password:",
        "username:",
        "__token__",
        "api-token",
        "Create a PyPI API token",
        "Use a PyPI API token",
        "publish with a PyPI token",
    ]:
        assert marker not in content


def test_release_checklist_documents_published_base_smoke_check():
    content = _release_checklist_text()

    assert "Post-publish PyPI validation for VAL-01" in content
    assert "python -m venv /tmp/corpulse-pypi-smoke" in content
    assert "/tmp/corpulse-pypi-smoke/bin/python -m pip install --upgrade pip" in content
    assert "/tmp/corpulse-pypi-smoke/bin/python -m pip install corpulse" in content
    assert "import corpulse" in content
    assert "from corpulse import Corpulse" in content
    assert "assert callable(Corpulse)" in content


def test_release_checklist_documents_published_qdrant_smoke_check():
    content = _release_checklist_text()

    assert "Post-publish PyPI validation for VAL-02" in content
    assert "python -m venv /tmp/corpulse-qdrant-smoke" in content
    assert "/tmp/corpulse-qdrant-smoke/bin/python -m pip install --upgrade pip" in content
    assert '/tmp/corpulse-qdrant-smoke/bin/python -m pip install "corpulse[qdrant]"' in content
    assert "import qdrant_client" in content
    assert "from corpulse import AsyncQdrantCorpulseClient, QdrantCorpulseClient" in content
    assert 'assert QdrantCorpulseClient.__name__ == "QdrantCorpulseClient"' in content
    assert 'assert AsyncQdrantCorpulseClient.__name__ == "AsyncQdrantCorpulseClient"' in content
    assert 'assert qdrant_client.__name__ == "qdrant_client"' in content
