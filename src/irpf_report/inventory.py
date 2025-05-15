from irpf_report.investments import Position, Investment


class Inventory:
    investments: dict[str, Investment]

    def __init__(
        self,
        current_positions: list[Position],
        previous_positions: list[Position] | None,
    ) -> None:
        if previous_positions is None:
            previous_positions = list()

        self.investments = self._init_investments(current_positions, previous_positions)

    @staticmethod
    def _init_investments(current: list[Position], previous: list[Position]) -> dict[str, Investment]:
        investments: dict[str, Investment] = dict()
        for position in current:
            if position.asset.key not in investments:
                investments[position.asset.key] = Investment(asset=position.asset)

            investments[position.asset.key].add_current(position)

        for position in previous:
            if position.asset.key not in investments:
                investments[position.asset.key] = Investment(asset=position.asset)

            investments[position.asset.key].add_previous(position)

        return investments

    def get_investments(self) -> list[Investment]:
        return list(self.investments.values())
