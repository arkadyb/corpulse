# Contributing

Thanks for helping improve corpulse. This repository is public and open to pull
requests, but all changes are reviewed before they are merged.

## Contribution Rules

- Open an issue first for large changes, new integrations, or public API changes.
- Keep pull requests focused and small enough to review.
- Add or update tests when changing behavior.
- Do not include credentials, tokens, private data, generated local databases, or
  machine-specific files.
- Contributions are provided under the repository license, MPL-2.0.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev,qdrant,fastapi,postgres,postgres-async]"
python -m pytest
```

## Pull Request Review

Pull requests must pass CI and be reviewed by a maintainer before merge.
Maintainers may ask for changes to tests, documentation, API shape, or scope.

For contributor safety, do not post security vulnerabilities in public issues or
pull requests. Use the private reporting process in `SECURITY.md`.
