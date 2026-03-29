from __future__ import annotations

from src.domain.api_contract import ApiContract


class ApiCatalogRegistry:
    def __init__(self, contracts: list[ApiContract]) -> None:
        self._contracts = contracts

    def list_all(self) -> list[ApiContract]:
        return self._contracts[:]

