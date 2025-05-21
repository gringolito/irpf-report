from collections.abc import Iterable
import logging

from irpf_report.investments import Position, Investment, Transaction


class Inventory:
    def __init__(self) -> None:
        self.investments: dict[str, Investment] = dict()

    def add_current_positions(self, current: Iterable[Position]) -> None:
        for position in current:
            if position.asset.key not in self.investments:
                self.investments[position.asset.key] = Investment(asset=position.asset)
            else:
                self.investments[position.asset.key].asset.update_cnpj(position.asset.get_cnpj())

            self.investments[position.asset.key].add_current_position(position)

    def add_previous_positions(self, previous: Iterable[Position]) -> None:
        for position in previous:
            if position.asset.key not in self.investments:
                self.investments[position.asset.key] = Investment(asset=position.asset)
            else:
                self.investments[position.asset.key].asset.update_cnpj(position.asset.get_cnpj())

            self.investments[position.asset.key].add_previous_position(position)

    def add_transactions(self, transactions: Iterable[Transaction]) -> None:
        for transaction in transactions:
            if transaction.ticker not in self.investments:
                logging.warning(f"Could not find a position for ticker: {transaction.ticker}")
                logging.info(f"Skipping transactions for {transaction.ticker} ...")
                continue

            self.investments[transaction.ticker].add_transaction(transaction)

    def get_investments(self) -> list[Investment]:
        return list(self.investments.values())
