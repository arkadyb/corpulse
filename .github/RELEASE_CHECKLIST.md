# First Release Checklist

Use this as the operational checklist for the first release with Trusted Publishing.

## Preflight

- Confirm the GitHub `pypi` environment has required reviewers or an equivalent explicit approval gate before the first production release.
- Do not create or use a PyPI API token for this workflow.
- Do not store PYPI_API_TOKEN, TEST_PYPI_API_TOKEN, or any PyPI password secret for this workflow.

## Version bump

- Bump the package version in the release branch and commit it before building.
- Create the release tag with `git tag v${VERSION}`.

## Build artifacts

- Build the release artifacts with `python -m build`.
- Verify the local `dist/` contents look correct before publishing.

## TestPyPI publish

- Run the Release workflow with `workflow_dispatch` to publish the tagged build to TestPyPI.
- Confirm the workflow uses Trusted Publishing and the `testpypi` environment.

## TestPyPI validation

- In a clean virtual environment, install from TestPyPI with:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ corpulse
```

- Confirm the package imports and the base install is usable.
- Confirm dependency resolution succeeds with PyPI as the fallback index.

## Production PyPI publish

- After TestPyPI validation passes, push the version tag with `git push origin v${VERSION}`.
- Confirm the workflow publishes to the `pypi` environment from tags that match `v*`.
- Confirm the production job uses Trusted Publishing and not long-lived credentials.

## Post-publish PyPI validation for VAL-01

- In a clean virtual environment, run:

```bash
python -m venv /tmp/corpulse-pypi-smoke
/tmp/corpulse-pypi-smoke/bin/python -m pip install --upgrade pip
/tmp/corpulse-pypi-smoke/bin/python -m pip install corpulse
/tmp/corpulse-pypi-smoke/bin/python - <<'PY'
import corpulse
from corpulse import Corpulse

assert callable(Corpulse)
PY
```

- Verify the base import surface works after the public PyPI publish.

## Post-publish PyPI validation for VAL-02

- In a clean virtual environment, run:

```bash
python -m venv /tmp/corpulse-qdrant-smoke
/tmp/corpulse-qdrant-smoke/bin/python -m pip install --upgrade pip
/tmp/corpulse-qdrant-smoke/bin/python -m pip install "corpulse[qdrant]"
/tmp/corpulse-qdrant-smoke/bin/python - <<'PY'
import qdrant_client
from corpulse import AsyncQdrantCorpulseClient, QdrantCorpulseClient

assert QdrantCorpulseClient.__name__ == "QdrantCorpulseClient"
assert AsyncQdrantCorpulseClient.__name__ == "AsyncQdrantCorpulseClient"
assert qdrant_client.__name__ == "qdrant_client"
PY
```

- Verify the Qdrant wrapper import surface works after the public PyPI publish.
