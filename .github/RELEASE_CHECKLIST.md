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

## Post-publish smoke checks

- In a clean environment, run `python -m pip install corpulse`.
- In a clean environment, run `python -m pip install "corpulse[qdrant]"`.
- Verify the base import surface works after the public PyPI publish.
- Verify the Qdrant wrapper import surface works after the public PyPI publish.
