# Getting started

## Install

You need [uv](https://docs.astral.sh/uv/).

```bash
uv tool install git+https://github.com/conscioustahoe/fumi
```

## Run

```bash
fumi path/to/openapi.json
```

Or run `fumi` and pick a file in the browser. Fumi always uses port 3737.

## No OpenAPI file yet

Most frameworks can write one. With FastAPI:

```bash
python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > openapi.json
```

Keep it in your repo and Fumi follows it across branches.

## Signing in

Open **environment** at the bottom.

- **My browser session.** Sign in to your app in Brave or Chrome or Arc or Edge. Fumi uses that session when it sends. Nothing is copied or saved.
- **An API key.** Paste it once. It stays on your Mac and is never shown again.

## Working on Fumi

```bash
git clone https://github.com/conscioustahoe/fumi && cd fumi
uv sync
uv run pytest
uv run python examples/make_sample.py ~/fumi-sample
uv run fumi ~/fumi-sample/openapi.json
```

The sample is a small API with a few branches to try things on.
