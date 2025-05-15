"""
Parser module for handling investment position reports from Excel files.
Provides functionality to parse different types of investments including stocks,
BDRs, fixed income, treasury bonds, investment funds and stock loans.
"""

from decimal import Decimal
import pandas
import pathlib
import warnings

from irpf_report.assets import (
    StockExchangeListed,
    FixedIncome,
    Stock,
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
from irpf_report.investments import Position
from irpf_report.asset_types import StockType


class ExcelParser:
    """
    A parser for investment Excel files with multiple sheets containing financial positions.
    """

    def __init__(self, file_path: pathlib.Path) -> None:
        """
        Args:
            file_path (str): The file path to the excel spreadsheet to parse
        """
        self.path = file_path

    def get_available_sheets(self) -> list[int | str]:
        """Returns a list of available sheet names in the Excel file."""
        with pandas.ExcelFile(self.path, engine="openpyxl") as xls:
            return xls.sheet_names


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
    - Investment Funds: Handled by FundsParser
    - Fixed Income: Handled by FixedIncomeParser
    - Treasury Bonds: Handled by TreasuriesParser
    """

    def parse_report(self) -> list[Position]:
        """Parse the position report Excel file.

        Iterates through each sheet in the Excel file and uses the appropriate
        parser to extract the investment positions.

        Returns:
            List[Position]: A list of parsed positions from all sheets
        """
        parsers: dict[str, type[SheetParser]] = {
            "Acoes": StocksParser,
            "BDR": BDRParser,
            "Empréstimos": LoanParser,
            "Fundo de Investimento": FundsParser,
            "Renda Fixa": FixedIncomeParser,
            "Tesouro Direto": TreasuriesParser,
        }

        positions: list[Position] = list()
        for name, parser_cls in parsers.items():
            with warnings.catch_warnings():
                # Ignore workbook missing stylesheet warnings until the openpyxl team solves the issue
                warnings.simplefilter("ignore")
                sheet = pandas.read_excel(self.path, sheet_name=name, parse_dates=True, engine="openpyxl")
            parser = parser_cls(sheet)
            positions.extend(parser.parse_sheet())

        return positions


class SheetParser:
    """
    Base class for parsing individual Excel sheets containing investment positions.
    Provides validation and common parsing functionality for all sheet types.
    """

    def __init__(self, sheet: pandas.DataFrame):
        """
        Args:
            sheet (pandas.DataFrame): The sheet dataframe to parse
        """
        self.sheet = sheet
        self.required_columns = list()
        for attr in dir(self):
            if attr.startswith("COL_"):
                self.required_columns.append(self.__getattribute__(attr))

        self.validate()

    def validate(self) -> None:
        """Validate the sheet to ensure all required columns are present."""
        missing_columns = set(self.required_columns) - set(self.sheet.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

    def parse_sheet(self) -> list[Position]:
        """
        Parse a sheet holdings.

        Returns:
            List[Position]: List of parsed holdings
        """
        positions = list()

        for _, row in self.sheet.iterrows():
            if not self.is_valid(row):
                # End of valid entries, just stop processing
                break

            try:
                positions.append(self.parse_position(row))
            except Exception as e:
                print(f"Error parsing row: {row}")
                raise e

        return positions

    def is_valid(self, row: pandas.Series) -> bool:
        raise NotImplementedError(f"This method should be implemented on the derived class: {self.__class__}")

    def parse_position(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        raise NotImplementedError(f"This method should be implemented on the derived class: {self.__class__}")


class PositionReportSheetParser(SheetParser):
    COL_NAME = "Produto"
    COL_BROKER = "Instituição"
    COL_QUANTITY = "Quantidade"

    def is_valid(self, row: pandas.Series) -> bool:
        return not pandas.isna(row[self.COL_NAME])


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

    def parse_position(self, row: pandas.Series) -> Position:
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
            maturity_date=row[self.COL_MATURITY_DATE],
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)


class TreasuriesParser(PositionReportSheetParser):
    """Parser for Brazilian Treasuries (Tesouro Direto) investment sheets."""

    COL_MATURITY_DATE = "Vencimento"
    COL_INVESTED_AMOUNT = "Valor Aplicado"

    def parse_position(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        asset = Treasury(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            maturity_date=row[self.COL_MATURITY_DATE],
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
    def parse_type(type_str: str) -> StockType:
        """Convert the stock type string to its corresponding enum value.

        Args:
            type_str (str): The stock type string from the Excel sheet

        Returns:
            StockType: The corresponding stock type enum
        """
        return StockType[type_str]

    def parse_position(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        stock_type = self.parse_type(str(row[self.COL_TYPE]))
        asset = Stock(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=str(row[self.COL_TICKER]).strip(),
            cnpj=str(int(row[self.COL_CNPJ])).strip().zfill(14),
            type=stock_type,
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

    def parse_position(self, row: pandas.Series) -> Position:
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


class BDRParser(PositionReportSheetParser):
    """Parser for Brazilian Depositary Receipts (BDR) investment sheets."""

    COL_TICKER = "Código de Negociação"

    def parse_position(self, row: pandas.Series) -> Position:
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
        if ticker.endswith("3") or ticker.endswith("4"):
            return Stock
        return StockExchangeListed

    @staticmethod
    def parse_stock_type(ticker: str) -> StockType | None:
        if ticker.endswith("34"):
            return None
        if ticker.endswith("3"):
            return StockType.ON
        if ticker.endswith("4"):
            return StockType.PN
        return None

    def parse_position(self, row: pandas.Series) -> Position:
        """Parse a single row into a Position object.

        Args:
            row (pandas.Series): A row from the sheet

        Returns:
            Position: The parsed position object
        """
        ticker = self.parse_ticker(str(row[self.COL_NAME]).strip())
        asset_class = self.get_asset_class(ticker)
        stock_type = self.parse_stock_type(ticker)
        asset = asset_class(
            name=str(row[self.COL_NAME]).strip(),
            broker=str(row[self.COL_BROKER]).strip(),
            ticker=ticker,
            type=stock_type,
        )
        quantity = Decimal(str(row[self.COL_QUANTITY]))
        return Position(asset=asset, quantity=quantity)
