"""Craft FastAPI entry point。

起動時に `discover_systems()` で全 system を import し、
registry を確定させてから router を組み立てる。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from craft.api.errors import register_exception_handlers
from craft.api.routers import (
    analyses,
    components,
    configs,
    history,
    merge,
    runs,
    scaffold,
    schema,
    validate,
    verify,
    veriq_passthrough,
)
from craft.core.discovery import discover_systems

TAGS_METADATA = [
    {"name": "schema", "description": "Pydantic JSON Schema 配信"},
    {"name": "components", "description": "TOML 上のインスタンス CRUD（ETag / If-Match）"},
    {"name": "configs", "description": "Config CRUD（Singleton / MultiInstance）"},
    {"name": "analyses", "description": "@analysis 関数の自動 API（一覧 / 実行）"},
    {"name": "validate", "description": "Pydantic schema validation only"},
    {"name": "verify", "description": "veriq 検証実行"},
    {"name": "runs", "description": "verification run history"},
    {"name": "merge", "description": "systems/*/data.toml → generated/merged.toml"},
    {"name": "scaffold", "description": "registry → data.toml 雛形生成"},
    {"name": "veriq", "description": "veriq pass-through (graph / trace / schema)"},
    {"name": "history", "description": "git log / diff"},
    {"name": "meta", "description": "health / version"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    discover_systems()
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
app.include_router(configs.router)
app.include_router(analyses.router)
app.include_router(validate.router)
app.include_router(verify.router)
app.include_router(runs.router)
app.include_router(merge.router)
app.include_router(scaffold.router)
app.include_router(veriq_passthrough.router)
app.include_router(history.router)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
