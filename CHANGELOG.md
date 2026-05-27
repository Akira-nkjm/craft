# Changelog

## Unreleased

### Breaking Changes

#### GET /components/{system}/{component} — singleton `instances` format (PR #34, issue #11)

The `instances` field for singleton components now contains the component's raw data dict
directly (same fields you'd see in a single-instance GET), instead of the previous format
that wrapped data under a key.

**Before PR #34**:
```json
{
  "system": "cdh", "component": "obc", "cardinality": "single",
  "instances": {"obc": {"spec": {...}, "design": {...}}}
}
```

**After PR #34** (current):
```json
{
  "system": "cdh", "component": "obc", "cardinality": "single",
  "instances": {"spec": {...}, "design": {...}}
}
```

**Migration**: Access `body["instances"]["spec"]` directly instead of
`body["instances"]["obc"]["spec"]`.

#### ETag policy unified across CLI and MCP (issue #13)

**Before**: `craft put/patch/delete` and MCP write tools silently fetched the
current ETag when `--etag` / `"etag"` was omitted, effectively disabling
optimistic concurrency control.

**After**: Omitting the ETag now raises an error by default (`required` mode).
Pass `--auto-etag` (CLI) or `"auto_etag": true` (MCP payload) to restore the
previous auto-fetch behaviour. Note that auto-fetch bypasses race-condition
detection.

**Affected CLI commands**:
- `craft put <sys> <comp> <inst>` — add `--etag <value>` or `--auto-etag`
- `craft patch <sys> <comp> <inst>` — add `--etag <value>` or `--auto-etag`
- `craft delete <sys> <comp> <inst>` — add `--etag <value>` or `--auto-etag`
- `craft spec set <sys> <comp>` — add `--etag <value>` or `--auto-etag`
  (only required when a shared spec already exists; first-time creation is unaffected)

**Affected MCP handlers**:
- `handle_patch_instance` / `handle_delete_instance`
- `handle_patch_config_instance` / `handle_delete_config_instance`
- `handle_set_shared_spec`

All handlers now require `"etag"` in the payload, or `"auto_etag": true` to
re-enable auto-fetch.

### New

- `core/concurrency.py`: `resolve_expected_etag(provided, mode, *, fetch)` —
  centralised ETag resolution logic shared by all write surfaces.
  `mode="required"` raises `PreconditionRequired` when no ETag is supplied;
  `mode="auto"` delegates to the `fetch()` callable.

### Changed

#### MCP `set_<config>` / `set_<name>` (multi-instance) — optional ETag now honoured (PR #37, issue #53)

MCP tool handlers that do a full-replace of a config entry previously ignored any `"etag"`
field in the payload. They now forward it to the underlying write operation.

**Semantics (upsert — not a breaking change)**:
- No `"etag"` in payload → write proceeds without a concurrency check (same as before)
- `"etag"` provided, record **exists** → ETag is validated; mismatch returns `{"error": ...}`
- `"etag"` provided, record **does not exist** → ETag is ignored (creation path)

**Affected handlers**: `handle_set_config` (singleton), `handle_set_config_instance` (multi)

### Fixed

- `mcp_server/handlers.py`: `handle_set_config_instance` was passing the entire payload
  dict (including the `"data"` wrapper key and `"etag"`) to Pydantic `model_validate`
  instead of the unwrapped model fields. Since all Config models use `extra="forbid"`,
  this caused a `validation_error` on every call. Now extracts `payload["data"]` before
  validation, matching the pattern used by `handle_set_config`. (issue #53)
