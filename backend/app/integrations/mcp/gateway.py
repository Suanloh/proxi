import asyncio
from collections.abc import Callable
from datetime import timedelta

from mcp import types
from mcp.server import Server
from mcp.shared.memory import create_connected_server_and_client_session

from ...schs.authz import ActionRequest
from ...schs.integrations import CatalogResult
from ...svcs.integrations import MCP_CATALOG, IntegrationExecutionError
from ..local_agent.catalog import lookup_catalog

_TIMEOUT = 5


def catalog_server(lookup: Callable[[str], CatalogResult] = lookup_catalog) -> Server:
    server = Server(MCP_CATALOG.integration)

    @server.list_tools()
    async def tools() -> list[types.Tool]:
        return [types.Tool(
            name=MCP_CATALOG.tool,
            description="Look up the PROXI demo catalog entry.",
            inputSchema={"type": "object", "properties": {"resource": {"const": MCP_CATALOG.resource}},
                         "required": ["resource"], "additionalProperties": False},
            outputSchema=CatalogResult.model_json_schema(),
        )]

    @server.call_tool()
    async def call(name: str, arguments: dict) -> dict:
        if name != MCP_CATALOG.tool or arguments != {"resource": MCP_CATALOG.resource}:
            raise IntegrationExecutionError("Unsupported catalog call")
        return lookup(MCP_CATALOG.resource).model_dump()

    return server


class McpCatalogGateway:
    def __init__(self, server_factory: Callable[[], Server] = catalog_server) -> None:
        self._server_factory = server_factory

    async def _call(self) -> CatalogResult:
        async with asyncio.timeout(_TIMEOUT):
            async with create_connected_server_and_client_session(
                self._server_factory(), read_timeout_seconds=timedelta(seconds=_TIMEOUT),
            ) as client:
                response = await client.call_tool(MCP_CATALOG.tool, {"resource": MCP_CATALOG.resource})
                if response.isError:
                    raise IntegrationExecutionError("MCP tool returned an error")
                return CatalogResult.model_validate(response.structuredContent)

    def execute(self, request: ActionRequest) -> CatalogResult:
        if (request.integration_type, request.action, request.resource) != (
            MCP_CATALOG.kind, MCP_CATALOG.action, MCP_CATALOG.resource,
        ):
            raise IntegrationExecutionError("Unsupported MCP action")
        try:
            return asyncio.run(self._call())
        except Exception:
            raise IntegrationExecutionError("MCP tool execution failed") from None
