# Development

## Setup

```bash
uv sync --dev
```

## Running Tests

```bash
uv run pytest
```

## Making a Release

1. **Update version and changelog**

   - Bump `version` in `pyproject.toml`
   - Move unreleased changes in `CHANGELOG.md` under a new version heading with today's date
   - Run `uv lock` to update `uv.lock`

2. **Commit and tag**

   ```bash
   git add pyproject.toml CHANGELOG.md uv.lock
   git commit -m "Release vX.Y.Z"
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   ```

3. **Build**

   ```bash
   uv build
   ```

4. **Upload to PyPI**

   ```bash
   uv run twine upload dist/uv_import_constraint_dependencies-X.Y.Z*
   ```

   Requires a PyPI API token configured in `~/.pypirc` or via `TWINE_USERNAME`/`TWINE_PASSWORD` environment variables.

5. **Push**

   ```bash
   git push && git push --tags
   ```
