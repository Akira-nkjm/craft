# Changelog

## Unreleased

### Breaking Changes

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

### Fixed

- `mcp_server/handlers.py`: corrected Python 2 `except TypeError, ValueError:`
  syntax to `except (TypeError, ValueError):` in `handle_history`.
