from ...schs.authz import ActionRequest
from ...schs.integrations import CatalogResult
from ...svcs.integrations import LOCAL_CATALOG, IntegrationExecutionError


def lookup_catalog(resource: str) -> CatalogResult:
    if resource != "catalog:proxi":
        raise IntegrationExecutionError("Unknown catalog entry")
    return CatalogResult(entry="proxi", category="demo")


class LocalCatalogAdapter:
    def execute(self, request: ActionRequest) -> CatalogResult:
        if (request.integration_type, request.action) != (LOCAL_CATALOG.kind, LOCAL_CATALOG.action):
            raise IntegrationExecutionError("Unsupported local action")
        return lookup_catalog(request.resource)
