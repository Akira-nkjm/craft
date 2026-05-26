"""Craft FastAPI entry point。

起動時に `discover_subsystems()` で全 subsystem を import し、
registry を確定させてから router を組み立てる。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.errors import register_exception_handlers
from api.routers import analyses, components, merge, scaffold, schema, verify
from core.discovery import discover_subsystems

TAGS_METADATA = [
    {"name": "schema", "description": "Pydantic JSON Schema 配信"},
    {"name": "components", "description": "TOML 上のインスタンス CRUD（ETag / If-Match）"},
    {"name": "analyses", "description": "@analysis 関数の自動 API（一覧 / 実行）"},
    {"name": "verify", "description": "veriq 検証実行"},
    {"name": "merge", "description": "subsystems/*/data.toml → generated/merged.toml"},
    {"name": "scaffold", "description": "registry → data.toml 雛形生成"},
    {"name": "meta", "description": "health / version"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    discover_subsystems()
    yield


app = FastAPI(
    title="Craft API",
    description="Concept Registry for Automated spacecraFT design",
    version="0.1.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(schema.router)
app.include_router(components.router)
app.include_router(analyses.router)
app.include_router(verify.router)
app.include_router(merge.router)
app.include_router(scaffold.router)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
