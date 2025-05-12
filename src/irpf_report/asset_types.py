from enum import Enum, auto


class StockType(Enum):
    """
    Enum representing different types of stocks.
    """

    ON = auto()  # Ordinary Stocks
    PN = auto()  # Preferential Stocks
    UNIT = auto()  # Stock UNITs
