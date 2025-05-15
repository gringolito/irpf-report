from dataclasses import dataclass, field
from decimal import Decimal
from irpf_report.assets import Asset


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

    def add_current(self, position: Position) -> None:
        self.current_quantity += position.quantity
        self.current_invested_amount += position.invested_amount

    def add_previous(self, position: Position) -> None:
        self.previous_quantity += position.quantity
        self.previous_invested_amount += position.invested_amount

    def is_closed(self) -> bool:
        return self.current_quantity == 0
