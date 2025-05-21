from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum, auto

from irpf_report.assets import Asset


class Operation(Enum):
    BUY = auto()
    SELL = auto()


@dataclass
class Transaction:
    date: date
    operation: Operation
    broker: str
    ticker: str
    quantity: int
    price: Decimal
    total_amount: Decimal


@dataclass
class Position:
    """
    An asset position representation with its essential information.

    Attributes:
        asset (Asset): The holding asset
        quantity (Decimal): Number of holdings
        invested_amount (Optional[Decimal]): Amount invested (defaults to: None)
    """

    asset: Asset
    quantity: Decimal
    invested_amount: Decimal = field(default=Decimal(0))


@dataclass
class Investment:
    """
    An asset investment holding representation with its essential information.

    Attributes:
        asset (Asset): The inventoried asset
        current_invested_amount (Decimal): Amount invested (to be declared in the current year)
        current_quantity (Decimal): Number of holdings (to be declared in the current year)
        previous_invested_amount (Decimal): Amount invested (as declared in the previous year)
        previous_quantity (Decimal): Number of holdings (as declared in the previous year)
    """

    asset: Asset
    current_invested_amount: Decimal = field(default=Decimal(0))
    current_quantity: Decimal = field(default=Decimal(0))
    previous_invested_amount: Decimal = field(default=Decimal(0))
    previous_quantity: Decimal = field(default=Decimal(0))
    transactions_balance_quantity: Decimal = field(default=Decimal(0))
    transactions_balance_amount: Decimal = field(default=Decimal(0))
    transactions: list[Transaction] = field(default_factory=list)
    latest_sell_date: date = field(default=date(year=1970, month=1, day=1))

    def add_current_position(self, position: Position) -> None:
        self.current_quantity += position.quantity
        self.current_invested_amount += position.invested_amount

    def add_previous_position(self, position: Position) -> None:
        self.previous_quantity += position.quantity
        self.previous_invested_amount += position.invested_amount
        if self.asset.is_listed():
            self.current_invested_amount += position.invested_amount

    def add_transaction(self, transaction: Transaction) -> None:
        if transaction.operation == Operation.BUY:
            self.transactions_balance_quantity += transaction.quantity
            self.transactions_balance_amount += transaction.total_amount
            self.current_invested_amount += transaction.total_amount
        elif transaction.operation == Operation.SELL:
            self.transactions_balance_quantity -= transaction.quantity
            self.transactions_balance_amount -= transaction.total_amount
            self.current_invested_amount -= transaction.total_amount
            if transaction.date > self.latest_sell_date:
                self.latest_sell_date = transaction.date
        else:
            raise ValueError(f"Invalid transaction for {self.asset.key}: operation = {transaction.operation}")

        self.transactions.append(transaction)

    def is_closed(self) -> bool:
        return self.current_quantity == 0

    @property
    def result(self) -> Decimal:
        return (self.previous_invested_amount + self.transactions_balance_amount).copy_negate()

    def has_missing_transactions(self) -> bool:
        if not self.asset.is_listed():
            return False
        return self.previous_quantity + self.transactions_balance_quantity != self.current_quantity

    def repeat_amount(self) -> bool:
        return all(
            [
                self.previous_invested_amount == self.current_invested_amount,
                self.previous_quantity == self.current_quantity,
            ]
        )
