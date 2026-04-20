# Releasing `data-juicer-openlineage`

## Prerequisites

- The repository is pushed to GitHub.
- PyPI trusted publishing is configured for this repository, or you are intentionally using a different publish path.
- The schema base URL in `data_juicer_openlineage/facets.py` points at the correct GitHub repository.

## Local verification

Run these commands before cutting a release:

```bash
pip install -e .[dev]
pytest
python -m build
python -m twine check dist/*
```

If you are developing against a local `py-data-juicer` checkout, install that first:

```bash
pip install -e /path/to/py-data-juicer
pip install -e .[dev]
```

## Release steps

1. Update the version in `pyproject.toml`.
2. Review `README.md` and schema URLs if the repository owner or default branch changed.
3. Run the local verification steps.
4. Commit and tag the release, for example `v0.1.0`.
5. Push the tag and create a GitHub Release, or publish a Release from the GitHub UI.
6. The `Publish` workflow will build the package and upload it to PyPI.

## Notes

- The CI workflow validates both tests and package metadata on every PR.
- The publish workflow assumes trusted publishing to the real PyPI index.
- If you want a TestPyPI lane later, the easiest extension is adding a second publish job with `repository-url` set to TestPyPI.
