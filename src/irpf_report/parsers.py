"""
Parser module for handling investment position reports from Excel files.
Provides functionality to parse different types of investments including stocks,
BDRs, fixed income, treasury bonds, investment funds and stock loans.
"""

from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
import logging
import pandas
import pathlib
from typing import Any
import warnings

from irpf_report.assets import (
    Asset,
    StockExchangeListed,
    FixedIncome,
    Stock,
    ON,
    PN,
    UNIT,
    FII,
    FIDC,
    ETF,
    BDR,
    FIIReceipt,
    CDB,
    LCI,
    LCA,
    Treasury,
)
from irpf_report.investments import Position, Transaction, Operation
from irpf_report.utils import search_asset_type_online


class ExcelParser(metaclass=ABCMeta):
    """
    A parser for investment Excel files with multiple sheets containing financial positions.
    """

    required_sheets: Iterable[str | int] = set()

    def __init__(self, file_path: pathlib.Path) -> None:
        """
        Args:
            file_path (str): The file path to the excel spreadsheet to parse
        """
        self.path = file_path
        self.validate()

    def validate(self) -> None:
        """Validate the workbook to ensure all required sheets are present."""
        missing_sheets = set(self.required_sheets) - set(self.get_available_sheets())
        if missing_sheets:
            raise ValueError(f"Missing required sheet(s): {missing_sheets}")

    def get_available_sheets(self) -> list[int | str]:
        """Returns a list of available sheet names in the Excel file."""
        with warnings.catch_warnings():
            # Ignore workbook missing stylesheet warnings until the openpyxl team solves the issue
            warnings.simplefilter("ignore")
            with pandas.ExcelFile(self.path, engine="openpyxl") as xls:
                return xls.sheet_names

    def read_sheet(self, sheet_name) -> pandas.DataFrame:
        with warnings.catch_warnings():
            # Ignore workbook missing stylesheet warnings until the openpyxl team solves the issue
            warnings.simplefilter("ignore")
            return pandas.read_excel(self.path, sheet_name=sheet_name, parse_dates=True, engine="openpyxl")

    @abstractmethod
    def parse_report(self) -> list[Any]:
        """Parse the report from the Excel file.

        Iterates through each sheet in the Excel file and uses the appropriate
        parser to extract the objects.

        Returns:
            List[Any]: A list of parsed objects from the Excel file
        """
        pass


class SheetParser(metaclass=ABCMeta):
    """
    Base class for parsing individual Excel sheets containing investment positions.
    Provides validation and common parsing functionality for all sheet types.
    """

    DATA_VALID_COLUMN: str | None = None

    def __init__(self, sheet: pandas.DataFrame) -> None:
        """
        Args:
            sheet (pandas.DataFrame): The sheet dataframe to parse
        """
        self.sheet = sheet
        self.required_columns: set[str] = set()
        for attr in dir(self):
            if attr.startswith("COL_"):
                self.required_columns.add(self.__getattribute__(attr))

        self.validate()

    def validate(self) -> None:
        """Validate the sheet to ensure all required columns are present."""
        missing_columns = self.required_columns - set(self.sheet.columns)
        if missing_columns:
            raise ValueError(f"Missing required column(s): {missing_columns}")

    def parse_sheet(self) -> list[Any]:
        """
        Parse a sheet of items.

        Returns:
            List[Any]: List of parsed items
        """
        items = list()

        for _, row in self.sheet.iterrows():
            if not self.is_valid(row):
                # End of valid entries, just stop processing
                break

            try:
                items.append(self.parse_row(row))
            except Exception as e:
                logging.error(f"Error parsing row: {row}")
                raise e

        return items

    def is_valid(self, row: pandas.Series) -> bool:
        if self.DATA_VALID_COLUMN is None:
            return True
        return not pandas.isna(row[self.DATA_VALID_COLUMN])

    @abstractmethod
    def parse_row(self, row: pandas.Series) -> Any:
        """Parse a single row into a object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Any: The parsed object
        """
        pass


################################################################################################################
## B3 positions report parsers
################################################################################################################


class PositionReportParser(ExcelParser):
    """
    Parser for investment position reports that contain multiple sheets,
    each representing a different type of investment. This class orchestrates
    the parsing of each sheet using specialized parsers.

    Each sheet is parsed by a specialized parser class that knows how to handle
    the specific investment type:
    - Stocks (Ações): Handled by StocksParser
    - BDRs: Handled by BDRParser
    - Stock Loans (Empréstimos): Handled by LoanParser
    - Exchange Traded Funds (ETFs): Handled by ETFParser
    - Investment Funds: Handled by FundsParser
    - Fixed Income: Handled by FixedIncomeParser
    - Treasury Bonds: Handled by TreasuriesParser
    """

    def __init__(self, file_path) -> None:
        self.sheet_parsers: dict[str, type[PositionReportSheetParser]] = {
            "Acoes": StocksParser,
            "BDR": BDRParser,
            "Empréstimos": LoanParser,
            "ETF": ETFParser,
            "Fundo de Investimento": FundsParser,
            "Renda Fixa": FixedIncomeParser,
            "Tesouro Direto": TreasuriesParser,
        }
        super().__init__(file_path)

    def parse_report(self) -> list[Position]:
        """Parse the position report Excel file.

        Iterates through each sheet in the Excel file and uses the appropriate
        parser to extract the investment positions.

        Returns:
            List[Position]: A list of parsed positions from all sheets
        """
        positions: list[Position] = list()
        sheets = self.get_available_sheets()
        for sheet_name, parser_cls in self.sheet_parsers.items():
            if sheet_name not in sheets:
                logging.debug("Sheet %s is not available on the report. Skipping...", sheet_name)
                continue
            sheet = self.read_sheet(sheet_name)
            parser = parser_cls(sheet)
            positions.extend(parser.parse_sheet())

        return positions


class PositionReportSheetParser(SheetParser):
    COL_NAME = "Produto"
    COL_BROKER = "Instituição"
    COL_QUANTITY = "Quantidade"
    DATA_VALID_COLUMN = COL_NAME


class FixedIncomeParser(PositionReportSheetParser):
    """
    Parser for fixed income investment sheets.
    """

    COL_ISSUER = "Emissor"
    COL_MATURITY_DATE = "Vencimento"

    @staticmethod
    def get_asset_class(name: str) -> type[FixedIncome]:
        """Extract the fixed income class type from the product name.

        Args:
            name (str): The product name containing the type information

        Returns:
            type[FixedIncome]: The corresponding asset class
        """
        types_mapping = {
            "lci": LCI,
            "lca": LCA,
            "cdb": CDB,
        }
        type_str = name.split("-", 1)[0].strip().lower()
        return types_mapping[type_str]

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset_class = self.get_asset_class(str(row[self.COL_NAME]))
        asset = asset_class(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            issuer=str(row[self.COL_ISSUER]).strip().upper(),
            maturity_date=datetime.strptime(str(row[self.COL_MATURITY_DATE]).strip(), "%d/%m/%Y").date(),
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


class TreasuriesParser(PositionReportSheetParser):
    """Parser for Brazilian Treasuries (Tesouro Direto) investment sheets."""

    COL_MATURITY_DATE = "Vencimento"
    COL_INVESTED_AMOUNT = "Valor Aplicado"

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset = Treasury(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            maturity_date=datetime.strptime(str(row[self.COL_MATURITY_DATE]).strip(), "%d/%m/%Y").date(),
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        invested_amount = Decimal(str(row[self.COL_INVESTED_AMOUNT]))
        return Position(asset=asset, quantity=quantity, invested_amount=invested_amount)


class StockExchangeListedParser(PositionReportSheetParser):
    """
    Base parser for any stock exchange listed assets including stocks,
    BDRs, and investment funds.
    """

    COL_TICKER = "Código de Negociação"
    COL_TYPE = "Tipo"


class StocksParser(StockExchangeListedParser):
    """Parser for stocks (ações) investment sheets."""

    COL_CNPJ = "CNPJ da Empresa"

    @staticmethod
    def get_asset_class(type_str: str) -> type[Stock]:
        """Convert the stock type string to its corresponding enum value.

        Args:
            type_str (str): The stock type string from the Excel sheet

        Returns:
            StockType: The corresponding stock type enum
        """
        types_mapping = {
            "on": ON,
            "pn": PN,
            "unit": UNIT,
        }
        return types_mapping[type_str.lower()]

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        stock_class = self.get_asset_class(str(row[self.COL_TYPE]))
        asset = stock_class(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=str(row[self.COL_TICKER]).strip(),
            cnpj=str(int(row[self.COL_CNPJ])).strip().zfill(14),
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


class FundsParser(StockExchangeListedParser):
    """Parser for investment funds sheets including FIIs and FIDCs."""

    COL_CNPJ = "CNPJ do Fundo"

    @staticmethod
    def get_asset_class(type_str: str) -> type[StockExchangeListed]:
        """Map fund type strings to their corresponding asset class.

        Args:
            type_str (str): The fund type string from the Excel sheet

        Returns:
            type[StockExchangeListed]: The corresponding asset class
        """
        types_mapping = {
            "cotas": FII,
            "recibo": FIIReceipt,
            "fundo": FIDC,
        }
        return types_mapping[type_str.lower()]

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset_class = self.get_asset_class(str(row[self.COL_TYPE]))
        asset = asset_class(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=str(row[self.COL_TICKER]).strip(),
            cnpj=str(int(row[self.COL_CNPJ])).strip().zfill(14),
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


class ETFParser(FundsParser):
    @staticmethod
    def get_asset_class(type_str: str) -> type[StockExchangeListed]:
        return ETF


class BDRParser(PositionReportSheetParser):
    """Parser for Brazilian Depositary Receipts (BDR) investment sheets."""

    COL_TICKER = "Código de Negociação"

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset = BDR(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=str(row[self.COL_TICKER]).strip(),
            cnpj="N/A",
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


class LoanParser(PositionReportSheetParser):
    """Parser for stock lending position sheets."""

    @staticmethod
    def parse_ticker(name: str) -> str:
        """Extract the stock ticker from the loan product name.

        Args:
            name (str): The loan product name containing the ticker

        Returns:
            str: The extracted stock ticker
        """
        return name.split("-", 1)[0].strip()

    @staticmethod
    def get_asset_class(ticker: str) -> type[StockExchangeListed]:
        """Determine the stock type based on its ticker suffix.

        Args:
            ticker (str): The stock ticker

        Returns:
            type[StockExchangeListed]: The corresponding asset class
        """
        if ticker.endswith("34"):
            return BDR
        if ticker.endswith("3"):
            return ON
        if ticker.endswith("4"):
            return PN
        if ticker.endswith("11"):
            asset_type = search_asset_type_online(ticker)
            if asset_type == None:
                raise RuntimeError("Could not determine the asset class", ticker)

            if asset_type == "Stock":
                return UNIT
            if asset_type == "ETF":
                return ETF
            if asset_type == "Fund":
                return FII

        raise RuntimeError("Could not determine the asset class", ticker)

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        ticker = self.parse_ticker(str(row[self.COL_NAME]).strip())
        asset_class = self.get_asset_class(ticker)
        asset = asset_class(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=ticker,
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


################################################################################################################
## B3 transactions report parsers
################################################################################################################


class TransactionsReportParser(ExcelParser):
    sheet_name = "Negociação"
    required_sheets = set([sheet_name])

    def parse_report(self) -> list[Transaction]:
        sheet = self.read_sheet(self.sheet_name)
        parser = TransactionsSheetParser(sheet)
        return parser.parse_sheet()


class TransactionsSheetParser(SheetParser):
    """
    Parser for transactions sheets.
    """

    COL_DATE = "Data do Negócio"
    COL_OPERATION = "Tipo de Movimentação"
    COL_BROKER = "Instituição"
    COL_TICKER = "Código de Negociação"
    COL_QUANTITY = "Quantidade"
    COL_PRICE = "Preço"
    COL_TOTAL_AMOUNT = "Valor"

    @staticmethod
    def parse_operation(operation: str) -> Operation:
        operation_mapping = {
            "compra": Operation.BUY,
            "venda": Operation.SELL,
        }
        return operation_mapping[operation.lower()]

    @staticmethod
    def parse_ticker(ticker: str) -> str:
        if ticker.endswith("F"):
            return ticker[:-1]
        return ticker

    def parse_row(self, row: pandas.Series) -> Transaction:
        """Parse a single row into a Transaction object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Transaction: The parsed transaction object
        """
        operation = self.parse_operation(str(row[self.COL_OPERATION]).strip())
        ticker = self.parse_ticker(str(row[self.COL_TICKER]).strip())
        return Transaction(
            date=datetime.strptime(str(row[self.COL_DATE]).strip(), "%d/%m/%Y").date(),
            operation=operation,
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=ticker,
            quantity=int(row[self.COL_QUANTITY]),
            price=Decimal(str(row[self.COL_PRICE])),
            total_amount=Decimal(str(row[self.COL_TOTAL_AMOUNT])),
        )


################################################################################################################
## Last year inventory report parsers
################################################################################################################


class IRPFReportParser(ExcelParser):
    sheet_name = "Inventário"
    required_sheets = set([sheet_name])

    def __init__(self, file_path: pathlib.Path, last_year: int) -> None:
        self.last_year = last_year
        super().__init__(file_path)

    def parse_report(self) -> list[Position]:
        sheet = self.read_sheet(self.sheet_name)
        parser = InventorySheetParser(sheet, self.last_year)
        return parser.parse_sheet()


class InventorySheetParser(SheetParser):
    """
    Parser for inventory sheets.
    """

    COL_NAME = "Nome"
    COL_BROKER = "Instituição"
    COL_TYPE = "Tipo"
    COL_CNPJ = "CNPJ"
    COL_TICKER = "Código de Negociação"
    COL_MATURITY_DATE = "Data de Vencimento"
    COL_ISSUER = "Emissor"
    COL_QUANTITY = "Quantidade"

    def __init__(self, sheet: pandas.DataFrame, last_year: int) -> None:
        self.last_year = last_year
        self.COL_INVESTED_AMOUNT = f"Situação em {last_year}"
        super().__init__(sheet)

    @staticmethod
    def get_asset_class(asset_type: str) -> type[Asset]:
        types_mapping: dict[str, type[Asset]] = {
            "on": ON,
            "pn": PN,
            "unit": UNIT,
            "etf": ETF,
            "bdr": BDR,
            "fii": FII,
            "fiireceipt": FIIReceipt,
            "fidc": FIDC,
            "cdb": CDB,
            "lci": LCI,
            "lca": LCA,
            "treasury": Treasury,
        }
        return types_mapping[asset_type.lower()]

    def get_asset(self, row: pandas.Series) -> Asset:
        asset_class = self.get_asset_class(str(row[self.COL_TYPE]))
        maturity_date = (
            datetime.strptime(str(row[self.COL_MATURITY_DATE]).strip(), "%d/%m/%Y").date()
            if not pandas.isna(row[self.COL_MATURITY_DATE])
            else None
        )
        parameters = {
            "name": str(row[self.COL_NAME]).strip(),
            "broker": str(row[self.COL_BROKER]).strip(),
            "cnpj": str(row[self.COL_CNPJ]).strip(),
            "ticker": str(row[self.COL_TICKER]).strip(),
            "maturity_date": maturity_date,
            "issuer": str(row[self.COL_ISSUER]).strip(),
        }
        return asset_class.from_dict(parameters)

    def parse_row(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset = self.get_asset(row)
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        invested_amount = Decimal(str(row[self.COL_INVESTED_AMOUNT]))
        return Position(asset=asset, quantity=quantity, invested_amount=invested_amount)
