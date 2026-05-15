# Trusted Publishing Setup

Use GitHub Actions OIDC Trusted Publishing for release uploads.

Operational release steps live in [.github/RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

## TestPyPI

- owner: arkadyb
- repository: corpulse
- workflow: release.yml
- environment: testpypi

Rules:

- Do not create or use a PyPI API token for this workflow.
- The TestPyPI publish job uses OIDC Trusted Publishing through pypa/gh-action-pypi-publish@release/v1.
- Run the Release workflow with `workflow_dispatch` to publish to TestPyPI.

## Production PyPI

- owner: arkadyb
- repository: corpulse
- workflow: release.yml
- environment: pypi

GitHub environments:

- Create a testpypi environment.
- Create a pypi environment.
- Configure the pypi environment with required reviewers or an equivalent explicit approval gate before the first production release.
- Do not store PYPI_API_TOKEN, TEST_PYPI_API_TOKEN, or any PyPI password secret for this workflow.

Production release trigger:

- Production PyPI publishing runs only from tags that match v*.
- The workflow job guard is startsWith(github.ref, 'refs/tags/v').
