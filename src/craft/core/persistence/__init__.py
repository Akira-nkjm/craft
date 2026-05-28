"""core.persistence — runs, jobs, history persistence.

Note: re-exports are intentionally omitted to avoid a circular import:
  jobs → core.pipeline.verify → core.persistence.runs
If this package re-exported its submodules, importing `core.persistence`
during pipeline setup would form a cycle.

Import from submodules directly: `core.persistence.runs`, `.jobs`, `.history`.
"""
