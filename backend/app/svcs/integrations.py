from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Protocol

from ..models.records import AgentType
from ..schs.authz import ActionRequest, Reason
from ..schs.integrations import CatalogResult


@dataclass(frozen=True)
class ToolSpec:
    kind: AgentType
    integration: str
    tool: str
    action: str
    resource: str
    path: str


MCP_CATALOG = ToolSpec(AgentType.MCP, "catalog", "lookup", "mcp.catalog.lookup", "catalog:proxi",
                       "/mcp/servers/catalog/tools/lookup")
LOCAL_CATALOG = ToolSpec(AgentType.LOCAL, "local-agent", "catalog-lookup", "local.catalog.lookup", "catalog:proxi",
                         "/local-agent/tools/catalog-lookup")
SUPPORTED_TOOLS = (MCP_CATALOG, LOCAL_CATALOG)


class ToolAdapter(Protocol):
    def execute(self, request: ActionRequest) -> CatalogResult: ...


class IntegrationExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class IntegrationState:
    spec: ToolSpec
    enabled: bool


class _Registration:
    def __init__(self, adapter: ToolAdapter) -> None:
        self.adapter = adapter
        self.enabled = False
        self.lock = Lock()


class IntegrationRegistry:
    """Trusted process-local management for the built-in tool catalog."""

    def __init__(self) -> None:
        self._entries: dict[ToolSpec, _Registration] = {}
        self._lock = Lock()

    def register(self, spec: ToolSpec, adapter: ToolAdapter) -> None:
        if spec not in SUPPORTED_TOOLS:
            raise ValueError("Unsupported integration")
        with self._lock:
            if spec in self._entries:
                raise ValueError("Integration already registered")
            self._entries[spec] = _Registration(adapter)

    def _registered(self, spec: ToolSpec) -> _Registration:
        with self._lock:
            return self._entries[spec]

    def enable(self, spec: ToolSpec) -> None:
        self._set_enabled(spec, True)

    def disable(self, spec: ToolSpec) -> None:
        self._set_enabled(spec, False)

    def _set_enabled(self, spec: ToolSpec, enabled: bool) -> None:
        entry = self._registered(spec)
        with entry.lock:
            entry.enabled = enabled

    def inspect(self, spec: ToolSpec) -> IntegrationState:
        entry = self._registered(spec)
        with entry.lock:
            return IntegrationState(spec, entry.enabled)

    @contextmanager
    def dispatch(self, spec: ToolSpec) -> Iterator[tuple[ToolAdapter, bool]]:
        entry = self._registered(spec)
        # Prevent disable from returning while an already-started dispatch can still execute.
        with entry.lock:
            yield entry.adapter, entry.enabled


def tool_restriction(spec: ToolSpec, enabled: bool, request: ActionRequest) -> Reason | None:
    if not enabled:
        return Reason.ADAPTER_UNAVAILABLE
    if request.resource != spec.resource:
        return Reason.RESOURCE_OUT_OF_SCOPE
    return None
