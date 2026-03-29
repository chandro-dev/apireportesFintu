from __future__ import annotations

from src.application.services.api_catalog_registry import ApiCatalogRegistry


class ListApiCatalogUseCase:
    def __init__(self, registry: ApiCatalogRegistry) -> None:
        self._registry = registry

    def execute(self) -> list[dict[str, str]]:
        return [contract.to_dict() for contract in self._registry.list_all()]

