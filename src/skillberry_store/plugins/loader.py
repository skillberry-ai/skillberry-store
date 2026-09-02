"""Plugin loader for discovering and managing plugins."""

import logging
from typing import Dict, List, Optional, Any
from importlib.metadata import entry_points
from fastapi import FastAPI, Depends, HTTPException

from skillberry_store.access_control.config import AccessControlConfig
from skillberry_store.access_control.pdp import Subject
from skillberry_store.plugins.base import PluginBase
from skillberry_store.plugins.store_api import StoreAPI
from skillberry_store.plugins.config import PluginConfigStore
from skillberry_store.plugins import events as plugin_events

logger = logging.getLogger(__name__)


class PluginLoader:
    """Discovers and manages plugins via entry points.
    
    Plugins are discovered through the 'skillberry_store.plugins' entry point group.
    Each plugin must be a subclass of PluginBase.
    """
    
    def __init__(
        self,
        store_api: StoreAPI,
        config_store: Optional[PluginConfigStore] = None,
        acl_cfg: Optional[AccessControlConfig] = None,
    ):
        """Initialize the plugin loader.

        Args:
            store_api: StoreAPI instance to inject into plugins
            config_store: persisted enable/disable state (defaults to PluginConfigStore())
            acl_cfg: access-control config, source of the deployment-wide
                owner tenant. ``None`` means no deployment-wide default, so a
                plugin's owner comes from the per-plugin record or nowhere.
        """
        self.store_api = store_api
        self.acl_cfg = acl_cfg
        self.plugins: Dict[str, PluginBase] = {}
        self.config = config_store or PluginConfigStore()
        # Event dispatch consults admin enablement only; capability is handled
        # by each plugin's own internal guard.
        plugin_events.set_enabled_resolver(self.config.is_enabled)
        # …and the identity trigger-driven work runs as (P1). Resolved per
        # dispatch, not captured here: plugins register their handlers inside
        # __init__, before any tenant, session or config reload exists (§5.2).
        plugin_events.set_owner_resolver(self.owner_subject)
    
    def discover_plugins(self) -> List[str]:
        """Discover and load all available plugins.
        
        Plugins are discovered via the 'skillberry_store.plugins' entry point.
        Invalid plugins or those with missing dependencies are skipped with a warning.
        
        Returns:
            List of successfully loaded plugin names
        """
        discovered = []
        
        # Get all entry points for skillberry_store.plugins
        eps = entry_points()
        
        # Handle different return types from entry_points()
        if isinstance(eps, list):
            # Mocked or old-style list
            plugin_entries = eps
        elif hasattr(eps, 'select'):
            # Python 3.10+
            plugin_entries = eps.select(group='skillberry_store.plugins')
        else:
            # Python 3.9 dict-like
            plugin_entries = eps.get('skillberry_store.plugins', [])
        
        for entry_point in plugin_entries:
            try:
                # Load the plugin class
                plugin_class = entry_point.load()
                
                # Verify it's a PluginBase subclass
                if not isinstance(plugin_class, type) or not issubclass(plugin_class, PluginBase):
                    logger.warning(
                        f"Plugin '{entry_point.name}' is not a PluginBase subclass, skipping"
                    )
                    continue
                
                # Snapshot existing handlers, instantiate, then attribute any
                # newly-registered handlers to this plugin's slug.
                before = self._handler_snapshot()
                plugin = plugin_class()
                for func in self._handler_snapshot() - before:
                    plugin_events.register_handler_owner(func, entry_point.name)

                # Inject a per-plugin view of the store API. The view shares
                # the services but knows its own slug, which is what lets
                # enforcement point 2 attribute an outcome to a plugin and
                # resolve *whose* owner tenant applies (§2.4).
                plugin.set_store_api(self.store_api.for_plugin(entry_point.name))

                # Store the plugin
                self.plugins[entry_point.name] = plugin
                discovered.append(entry_point.name)
                
                logger.info(
                    f"Loaded plugin '{entry_point.name}': {plugin.metadata.name} v{plugin.metadata.version}"
                )
                
            except ImportError as e:
                logger.warning(
                    f"Plugin '{entry_point.name}' has missing dependencies: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to load plugin '{entry_point.name}': {e}",
                    exc_info=True
                )
        
        return discovered
    
    @staticmethod
    def _handler_snapshot() -> set:
        """Set of all handler callables currently in the global event registry."""
        snapshot = set()
        for handlers in plugin_events._event_handlers.values():
            snapshot.update(handlers)
        return snapshot

    # ── Owner tenant (P1, §5) ──────────────────────────────────────────── #

    def owner_tenant(self, slug: str) -> Optional[str]:
        """The tenant a plugin's autonomous work runs as, or ``None``.

        Precedence: the per-plugin record written when a tenant enabled the
        plugin → the deployment-wide default from the access-control config →
        none, at which point P5 applies and the plugin's outward calls fail.
        """
        recorded = self.config.get_owner(slug)
        if recorded:
            return recorded
        if self.acl_cfg is not None:
            return self.acl_cfg.plugin_owner_tenant
        return None

    def owner_subject(self, slug: str) -> Optional[Subject]:
        """``owner_tenant`` as a PDP Subject, with that tenant's groups."""
        tenant = self.owner_tenant(slug)
        if not tenant:
            return None
        groups = (
            self.acl_cfg.groups_for_tenant(tenant) if self.acl_cfg is not None else []
        )
        return Subject(tenant_id=tenant, groups=groups)

    def record_owner(self, slug: str, tenant_id: Optional[str]) -> None:
        """Record the acting tenant as this plugin's owner (no-op if absent).

        Called when a tenant enables a plugin. In ``disabled`` mode there is no
        subject on the request, so there is nothing to record and nothing is
        written (§2.5).
        """
        if not tenant_id:
            return
        self.config.set_owner(slug, tenant_id)

    def is_active(self, slug: str) -> bool:
        """Effective enablement: plugin is capable AND admin-enabled."""
        plugin = self.plugins.get(slug)
        if plugin is None:
            return False
        return plugin.is_enabled() and self.config.is_enabled(slug)

    def set_enabled(self, slug: str, value: bool) -> None:
        """Admin toggle for a plugin; persists and takes effect live."""
        if slug not in self.plugins:
            raise KeyError(slug)
        self.config.set_enabled(slug, value)

    def _make_router_guard(self, slug: str):
        """Build a dependency that 404s when the plugin is not active."""
        async def guard():
            if not self.is_active(slug):
                raise HTTPException(status_code=404, detail=f"Plugin '{slug}' is disabled")
        return guard

    def mount_routers(self, app: FastAPI):
        """Mount plugin routers to the FastAPI app.

        Routers are always mounted (so plugins can be toggled live without a
        restart) but carry a guard dependency that returns 404 while the plugin
        is disabled or not capable.

        Args:
            app: FastAPI application instance
        """
        for plugin_name, plugin in self.plugins.items():
            router = plugin.get_router()
            if router is None:
                continue

            prefix = f"/plugins/{plugin_name}"
            app.include_router(
                router,
                prefix=prefix,
                tags=["plugins", plugin_name],
                dependencies=[Depends(self._make_router_guard(plugin_name))],
            )

            logger.info(f"Mounted router for plugin '{plugin_name}' at {prefix} (guarded)")
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dict with plugin info, or None if plugin not found
        """
        plugin = self.plugins.get(plugin_name)
        if plugin is None:
            return None
        
        metadata = plugin.metadata
        ui_config = plugin.get_ui_config()
        owner = self.owner_tenant(plugin_name)
        status = plugin.get_status_message()
        # P5 is meant to be observable rather than merely fatal: an operator
        # should be able to see that a plugin has no identity before its first
        # trigger fails silently on the event path (§5.1, §8).
        if self._acl_enabled() and not owner:
            status = (
                f"{status} — no owner tenant assigned; "
                "autonomous actions will fail"
            )
        
        return {
            "slug": plugin_name,  # Entry point name used in URLs
            "name": metadata.name,
            "description": metadata.description,
            "version": metadata.version,
            "plugin_type": metadata.plugin_type.value,
            "author": metadata.author,
            "homepage": metadata.homepage,
            "enabled": self.is_active(plugin_name),
            "admin_enabled": self.config.is_enabled(plugin_name),
            "status": status,
            "owner_tenant": owner,
            "has_router": plugin.get_router() is not None,
            "has_cli": plugin.get_cli_commands() is not None,
            "has_ui": ui_config is not None,
            "ui_config": ui_config,
        }
    
    def _acl_enabled(self) -> bool:
        return self.acl_cfg is not None and self.acl_cfg.mode != "disabled"

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins.
        
        Returns:
            List of plugin info dicts
        """
        result = []
        for plugin_name in self.plugins.keys():
            info = self.get_plugin_info(plugin_name)
            if info is not None:
                result.append(info)
        return result

# Made with Bob