"""core.instances — TOML 上のインスタンス CRUD。

既存の `from core.instances import ...` を破壊しないよう、
すべての公開シンボルをここで再 export する。
"""

from ._common import (
    InstanceAlreadyExists,
    InstanceNotFound,
    SharedSpecConflict,
    SingletonNotInstanceable,
    compute_etag,
)
from .components import (
    create_instance,
    delete_instance,
    get_component_view,
    get_instance,
    get_shared_spec,
    list_component_view,
    list_instances,
    patch_instance,
    replace_instance,
    set_shared_spec,
)
from .configs import (
    delete_config_instance,
    get_config_instance,
    get_singleton_config,
    list_config_instances,
    patch_config_instance,
    set_config_instance,
    set_singleton_config,
)

__all__ = [
    # exceptions
    "InstanceAlreadyExists",
    "InstanceNotFound",
    "SharedSpecConflict",
    "SingletonNotInstanceable",
    # utilities
    "compute_etag",
    # component CRUD
    "create_instance",
    "delete_instance",
    "get_component_view",
    "get_instance",
    "get_shared_spec",
    "list_component_view",
    "list_instances",
    "patch_instance",
    "replace_instance",
    "set_shared_spec",
    # config CRUD
    "delete_config_instance",
    "get_config_instance",
    "get_singleton_config",
    "list_config_instances",
    "patch_config_instance",
    "set_config_instance",
    "set_singleton_config",
]
