# Public Repository Controls

Use these GitHub settings to keep the repository public while keeping incoming
contributions under maintainer control.

## Branch Protection for `main`

Settings -> Branches -> Add branch protection rule:

- Branch name pattern: `main`
- Require a pull request before merging
- Require approvals: `1`
- Require review from Code Owners
- Dismiss stale pull request approvals when new commits are pushed
- Require status checks to pass before merging
- Require branches to be up to date before merging
- Required checks:
  - `Python 3.10`
  - `Python 3.11`
  - `Python 3.12`
  - `Analyze Python`
- Require conversation resolution before merging
- Block force pushes
- Block deletions
- Do not allow bypassing the above settings unless you intentionally need an
  emergency maintainer path

## Actions Settings

Settings -> Actions -> General:

- Actions permissions: allow actions and reusable workflows.
- Workflow permissions: read repository contents permission.
- Disable "Allow GitHub Actions to create and approve pull requests" unless you
  intentionally use that automation later.

Settings -> Actions -> General -> Fork pull request workflows:

- Require approval for first-time contributors.
- Keep write tokens unavailable to pull requests from forks.

## Security Features

Settings -> Code security and analysis:

- Enable Dependabot alerts.
- Enable Dependabot security updates.
- Enable CodeQL default setup or keep the repository workflow in
  `.github/workflows/codeql.yml`.
- Enable private vulnerability reporting.

## Release Controls

The release workflow publishes through PyPI Trusted Publishing and GitHub
environments. Keep the `pypi` environment protected with required reviewers.
