# Pre-commit Setup

SurfSense already ships with a repository-level `.pre-commit-config.yaml` at the root.
Use the steps below to install and run it locally.

## Install

From the repository root, make sure the backend dev environment is synced and then install the hooks:

```bash
cd nbd_backend
uv sync --group dev
cd ..
pre-commit install
pre-commit install-hooks
```

If you are not using `uv`, install `pre-commit` with your preferred Python tool first, then run the same hook commands from the repo root.

## Run Manually

Run all hooks against the whole repository:

```bash
pre-commit run --all-files
```

Run only a specific hook when you are iterating on one area:

```bash
pre-commit run ruff --files nbd_backend/app/main.py
```

## Update Hooks

When `.pre-commit-config.yaml` changes, refresh the cached hook environments:

```bash
pre-commit clean
pre-commit install-hooks
```

## Bypass When Needed

To skip hooks for one commit, use:

```bash
git commit --no-verify
```

Use this sparingly and only when you know the change is safe.