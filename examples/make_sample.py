"""Create a small git repo with an OpenAPI file on a few branches for trying Fumi.

    uv run python examples/make_sample.py ~/Workspace/fumi-sample

The repo holds a tiny FastAPI service and its openapi.json. Fumi only reads the file.
You run the service yourself when you want to send requests.

Branches:
  main             health auth entities payments
  feature/refunds  adds two refund endpoints
  fix/broken-spec  openapi.json is cut short so it no longer parses
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

MAIN_PY = '''\
from fastapi import FastAPI

from app.routers import auth, entities, meta, payments{extra_import}

app = FastAPI(title="Sample payments API")
app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(entities.router)
app.include_router(payments.router){extra_include}
'''

STORE_PY = '''\
import secrets

ENTITIES: dict[str, dict] = {}
PAYMENTS: dict[str, dict] = {}
REFUNDS: dict[str, dict] = {}


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(4).upper()}"
'''

META_PY = '''\
from fastapi import APIRouter

router = APIRouter(tags=["meta"])


@router.get("/health", summary="Health check")
def health():
    return {"status": "ok"}
'''

AUTH_PY = '''\
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class Login(BaseModel):
    email: str
    password: str


@router.post("/login", summary="Log in")
def login(body: Login, response: Response):
    if body.password != "dev-password":
        raise HTTPException(401, "bad credentials")
    response.set_cookie("session", "sample-session", httponly=True, max_age=7200)
    return {"access_token": "sample-token", "token_type": "bearer", "expires_in": 3600}
'''

ENTITIES_PY = '''\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.store import ENTITIES, new_id

router = APIRouter(prefix="/entities", tags=["entities"])


class EntityIn(BaseModel):
    name: str
    country: str
    external_ref: str | None = None
    tags: list[str] = []


@router.get("", summary="List entities")
def list_entities(limit: int = 20, status: str | None = None):
    rows = [e for e in ENTITIES.values() if status is None or e["status"] == status]
    return {"data": rows[:limit]}


@router.post("", summary="Create entity", status_code=201)
def create_entity(body: EntityIn):
    entity = {"id": new_id("ent"), "status": "active", **body.model_dump()}
    ENTITIES[entity["id"]] = entity
    return {"data": entity}


@router.get("/{entity_id}", summary="Get entity")
def get_entity(entity_id: str):
    if entity_id not in ENTITIES:
        raise HTTPException(404, f"entity {entity_id} not found")
    return {"data": ENTITIES[entity_id]}
'''

PAYMENTS_PY = '''\
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.store import ENTITIES, PAYMENTS, new_id

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentIn(BaseModel):
    entity_id: str
    amount: int
    currency: str
    method: str = "card"
    memo: str | None = None


@router.get("", summary="List payments")
def list_payments(entity_id: str | None = None):
    return {"data": [p for p in PAYMENTS.values() if entity_id in (None, p["entity_id"])]}


@router.post("", summary="Create payment", status_code=201)
def create_payment(body: PaymentIn, response: Response):
    if body.entity_id not in ENTITIES:
        raise HTTPException(422, f"entity {body.entity_id} not found")
    payment = {"id": new_id("pay"), "status": "pending", **body.model_dump()}
    PAYMENTS[payment["id"]] = payment
    response.headers["Location"] = f"/payments/{payment['id']}"
    return {"data": payment}


@router.get("/{pay_id}", summary="Get payment")
def get_payment(pay_id: str):
    if pay_id not in PAYMENTS:
        raise HTTPException(404, f"payment {pay_id} not found")
    return {"data": PAYMENTS[pay_id]}
'''

REFUNDS_PY = '''\
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.store import PAYMENTS, REFUNDS, new_id

router = APIRouter(tags=["refunds"])


class RefundIn(BaseModel):
    amount: int
    reason: str


@router.post("/payments/{{pay_id}}/refunds", summary="Create refund", status_code=201)
def create_refund(pay_id: str, body: RefundIn):
    if pay_id not in PAYMENTS:
        raise HTTPException(404, f"payment {{pay_id}} not found")
    refund = {{"id": new_id("ref"), "payment_id": pay_id, "status": "processing", **body.model_dump()}}
    REFUNDS[refund["id"]] = refund
    return {{"data": refund}}


@router.get("/refunds/{{refund_id}}", summary="Get refund")
def get_refund(refund_id: str):
    if refund_id not in REFUNDS:
        raise HTTPException(404, f"refund {{refund_id}} not found")
    return {{"data": REFUNDS[refund_id]}}
'''

README = """\
# fumi-sample

A throwaway FastAPI service for trying Fumi. Run it with:

    uv run --with fastapi --with uvicorn uvicorn app.main:app --port 8077
"""

EXPORT = "import json, sys; from app.main import app; json.dump(app.openapi(), sys.stdout, indent=2)"
AUTHOR = ["-c", "user.name=fumi", "-c", "user.email=fumi@example.invalid"]


def git(dest: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=dest, check=True, capture_output=True)


def write(dest: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def export_spec(dest: Path) -> str:
    """The service's own openapi.json. Uses this interpreter since Fumi already depends on FastAPI."""
    out = subprocess.run([sys.executable, "-c", EXPORT], cwd=dest, check=True, capture_output=True, text=True)
    return json.dumps(json.loads(out.stdout), indent=2) + "\n"


def commit(dest: Path, message: str) -> None:
    git(dest, "add", "-A")
    git(dest, *AUTHOR, "commit", "-q", "-m", message)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    dest = Path(sys.argv[1]).expanduser().resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} already exists and is not empty")
    dest.mkdir(parents=True, exist_ok=True)

    write(dest, {
        "README.md": README,
        ".gitignore": "__pycache__/\n",
        "app/__init__.py": "",
        "app/routers/__init__.py": "",
        "app/store.py": STORE_PY,
        "app/routers/meta.py": META_PY,
        "app/routers/auth.py": AUTH_PY,
        "app/routers/entities.py": ENTITIES_PY,
        "app/routers/payments.py": PAYMENTS_PY,
        "app/main.py": MAIN_PY.format(extra_import="", extra_include=""),
    })
    write(dest, {"openapi.json": export_spec(dest)})
    git(dest, "init", "-q", "-b", "main")
    commit(dest, "Sample service and its OpenAPI file")

    git(dest, "checkout", "-q", "-b", "feature/refunds")
    write(dest, {
        "app/routers/refunds.py": REFUNDS_PY.format(),
        "app/main.py": MAIN_PY.format(extra_import=", refunds", extra_include="\napp.include_router(refunds.router)"),
    })
    write(dest, {"openapi.json": export_spec(dest)})
    commit(dest, "Add refunds")

    git(dest, "checkout", "-q", "-b", "fix/broken-spec")
    text = (dest / "openapi.json").read_text()
    write(dest, {"openapi.json": text[: len(text) // 2]})
    commit(dest, "Cut the spec short")
    git(dest, "checkout", "-q", "main")

    print(textwrap.dedent(f"""\
        Created {dest} on main (also feature/refunds and fix/broken-spec).
        Open it:      uv run fumi {dest / "openapi.json"}
        Run the API:  cd {dest} && uv run --with fastapi --with uvicorn uvicorn app.main:app --port 8077"""))


if __name__ == "__main__":
    main()
