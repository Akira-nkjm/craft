"""MCP tool handlers — registry / TOML / veriq の薄いラッパ。"""

from craft.mcp_server.handlers.analyses import handle_analysis
from craft.mcp_server.handlers.components import (
    handle_add_instance,
    handle_delete_instance,
    handle_get_component,
    handle_list_component_instances,
    handle_patch_instance,
    handle_set_shared_spec,
)
from craft.mcp_server.handlers.config_instances import (
    handle_delete_config_instance,
    handle_get_config_instance,
    handle_patch_config_instance,
    handle_set_config_instance,
)
from craft.mcp_server.handlers.configs import handle_get_config, handle_set_config
from craft.mcp_server.handlers.history import handle_diff, handle_history
from craft.mcp_server.handlers.introspection import (
    handle_get_schema,
    handle_list_introspection,
)
from craft.mcp_server.handlers.verify import handle_verify_all, handle_verify_single

__all__ = [
    "handle_add_instance",
    "handle_analysis",
    "handle_delete_config_instance",
    "handle_delete_instance",
    "handle_diff",
    "handle_get_component",
    "handle_get_config",
    "handle_get_config_instance",
    "handle_get_schema",
    "handle_history",
    "handle_list_component_instances",
    "handle_list_introspection",
    "handle_patch_config_instance",
    "handle_patch_instance",
    "handle_set_config",
    "handle_set_config_instance",
    "handle_set_shared_spec",
    "handle_verify_all",
    "handle_verify_single",
]
