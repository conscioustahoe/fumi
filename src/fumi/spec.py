"""Reading an OpenAPI file from disk. Fumi never runs or imports the service it describes."""

import json
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024


class SpecError(Exception):
    pass


def resolve(path: str | Path) -> Path:
    """An absolute path for a spec the user named. It has to be an existing file."""
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        raise SpecError(f"{p} is not a file")
    return p


def read(path: Path) -> dict:
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        raise SpecError(f"{path.name} doesn't exist here")
    if size > MAX_BYTES:
        raise SpecError(f"{path.name} is {size // (1024 * 1024)} MB and Fumi reads up to {MAX_BYTES // (1024 * 1024)} MB")
    try:
        doc = json.loads(path.read_bytes())
    except UnicodeDecodeError:
        raise SpecError(f"{path.name} is not UTF-8 text")
    except json.JSONDecodeError as e:
        raise SpecError(f"{path.name} is not valid JSON: {e.msg} at line {e.lineno} column {e.colno}")
    if not isinstance(doc, dict) or not str(doc.get("openapi", "")).startswith("3"):
        raise SpecError(f"{path.name} is not an OpenAPI 3 document (no \"openapi\": \"3.x\" field)")
    if not isinstance(doc.get("paths", {}), dict):
        raise SpecError(f"{path.name} has a \"paths\" field that is not an object")
    return doc
