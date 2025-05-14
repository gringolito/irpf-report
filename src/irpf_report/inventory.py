from irpf_report.holdings import Position, Holding


class Inventory:
    holdings: dict[str, Holding]

    def __init__(
        self,
        current_positions: list[Position],
        previous_positions: list[Position] | None,
    ) -> None:
        if previous_positions is None:
            previous_positions = list()

        self.holdings = self._init_holdings(current_positions, previous_positions)

    def _init_holdings(self, current: list[Position], previous: list[Position]) -> dict[str, Holding]:
        holdings: dict[str, Holding] = dict()
        for position in current:
            if position.asset.key not in holdings:
                holdings[position.asset.key] = Holding(asset=position.asset)

            holdings[position.asset.key].add_current(position)

        for position in previous:
            if position.asset.key not in holdings:
                holdings[position.asset.key] = Holding(asset=position.asset)

            holdings[position.asset.key].add_previous(position)

        return holdings

    def get_holdings(self) -> list[Holding]:
        return list(self.holdings.values())
