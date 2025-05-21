from abc import ABCMeta, abstractmethod
from collections.abc import Iterable
from decimal import Decimal
from openpyxl.styles import Alignment, Font  # type: ignore[attr-defined]
from openpyxl.worksheet.worksheet import Worksheet
import pandas
import pathlib
from typing import Any

from irpf_report.investments import Investment
from irpf_report.utils import format_date


FORMAT_CURRENCY_REAL_SIMPLE = "[$R$ ]#,##0.00_-"


class IRPFReport:
    def __init__(self, file_path: pathlib.Path, current_year: int) -> None:
        """
        Args:
            file_path (str): The file path to the excel spreadsheet to create the report
        """
        self.path = file_path
        self.current_year = current_year
        self.sheet_writers = {
            "Bens e Direitos": AssetsSheetWriter,
            "Inventário": InventorySheetWriter,
        }

    def generate_report(self, investments: Iterable[Investment]) -> None:
        with pandas.ExcelWriter(self.path) as xls:
            for sheet_name, writer_cls in self.sheet_writers.items():
                writer = writer_cls(xls, self.current_year)
                writer.write_sheet(sheet_name, investments)


class SheetWriter(metaclass=ABCMeta):
    def __init__(self, xls: pandas.ExcelWriter, current_year: int) -> None:
        self.xls = xls
        self.current_year = current_year
        self.header_columns: dict[str, str] = dict()

    def write_sheet(self, sheet_name: str, items: Iterable[Any]) -> None:
        data = [self._format_data_to_excel(item) for item in items if self._filter_data(item)]
        dataframe = pandas.DataFrame(data)
        dataframe.to_excel(self.xls, sheet_name=sheet_name, header=True, index=False, float_format="%.2f")
        self._set_header_columns(dataframe)
        self._set_header_style(self.xls.sheets[sheet_name])
        self._set_sheet_style(self.xls.sheets[sheet_name])

    def get_column(self, name: str) -> str:
        return self.header_columns[name]

    def _filter_data(self, item: Any) -> bool:
        return True

    @abstractmethod
    def _format_data_to_excel(self, item: Any) -> dict[str, Any]:
        pass

    def _set_header_columns(self, dataframe: pandas.DataFrame) -> None:
        for i, name in enumerate(dataframe.columns.values):
            char = chr(ord("A") + i)
            self.header_columns[name] = char

    def _set_header_style(self, sheet: Worksheet) -> None:
        header = Font(name="Helvetica", bold=True)
        center_wrapped = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for column in self.header_columns.values():
            sheet[f"{column}1"].style = "Normal"
            sheet[f"{column}1"].font = header
            sheet[f"{column}1"].alignment = center_wrapped

    def _set_sheet_style(self, sheet: Worksheet) -> None:
        pass


class AssetsSheetWriter(SheetWriter):
    def __init__(self, xls, current_year) -> None:
        super().__init__(xls, current_year)
        self.previous_year = current_year - 1

    def _format_data_to_excel(self, item: Investment) -> dict[str, Any]:
        asset = item.asset
        current_invested_amount = item.current_invested_amount if not item.is_closed() else Decimal(0)
        return {
            "Grupo": asset.get_group(),
            "Código": asset.get_code(),
            "CNPJ": asset.get_cnpj(),
            "Descrição": self._format_investment_description(item),
            "Código de Negociação": asset.get_ticker(),
            f"Situação em {self.previous_year}": float(item.previous_invested_amount),
            f"Situação em {self.current_year}": float(current_invested_amount),
            "Repetir valor": "Repetir" if item.repeat_amount() else "",
            "Observações": self._format_investment_notes(item),
        }

    def _set_sheet_style(self, sheet: Worksheet) -> None:
        self._set_column_number_format(sheet)
        self._set_column_alignment(sheet)
        self._set_column_dimensions(sheet)

    def _format_investment_description(self, investment: Investment) -> str:
        asset = investment.asset
        description = asset.get_description_fmt() % investment.current_quantity

        if investment.is_closed() and not asset.has_matured(self.current_year):
            closed_date = investment.latest_sell_date
            result = investment.result
            loss_or_profit = "lucro" if result >= 0 else "prejuízo"
            result = abs(result)
            description += f" - Posição encerrada em {format_date(closed_date)} com {loss_or_profit} de R$ {result:.2f}"

        return description

    @staticmethod
    def _format_investment_notes(investment: Investment) -> str:
        notes: list[str] = list()
        if investment.previous_quantity > 0 and investment.previous_invested_amount == 0:
            notes.append("Situação no ano anterior não disponível, verificar último valor declarado")
        if investment.has_missing_transactions():
            notes.append("Verificar outros eventos acionários como: desdobramentos, grupamentos e/ou bonificações")
        return "\n".join(notes)

    def _set_column_dimensions(self, sheet: Worksheet) -> None:
        offsets = {
            "CNPJ": 1,
            "Descrição": -24,
            "Código de Negociação": 8,
            f"Situação em {self.previous_year}": 8,
            f"Situação em {self.current_year}": 8,
            "Repetir valor": 2,
        }
        for header, offset in offsets.items():
            column = self.get_column(header)
            length = max(len(str(cell.value)) for cell in sheet[column] if cell.row != 1)
            sheet.column_dimensions[column].width = length + offset

        # Notes column has wrapping text alignment set, so the max length should be calculated differently
        column = self.get_column("Observações")
        length = max(len(str(line)) for cell in sheet[column] for line in cell.value.split("\n"))
        sheet.column_dimensions[column].width = length - 12

    def _set_column_number_format(self, sheet: Worksheet) -> None:
        number_formats = {
            f"Situação em {self.previous_year}": FORMAT_CURRENCY_REAL_SIMPLE,
            f"Situação em {self.current_year}": FORMAT_CURRENCY_REAL_SIMPLE,
        }
        for header, format in number_formats.items():
            column = self.get_column(header)
            for cell in sheet[column]:
                cell.number_format = format

    def _set_column_alignment(self, sheet: Worksheet) -> None:
        center = Alignment(horizontal="center")
        wrap_text = Alignment(wrap_text=True)
        alignments = {
            "Grupo": center,
            "Código": center,
            "Observações": wrap_text,
        }

        for header, alignment in alignments.items():
            column = self.get_column(header)
            for cell in sheet[column]:
                if cell.row == 1:
                    continue
                cell.alignment = alignment


class InventorySheetWriter(SheetWriter):
    def _filter_data(self, item: Investment) -> bool:
        return not item.is_closed()

    def _format_data_to_excel(self, item: Investment) -> dict[str, Any]:
        asset = item.asset
        return {
            "Nome": asset.name,
            "Instituição": asset.broker,
            "Tipo": asset.get_type(),
            "CNPJ": asset.get_cnpj(),
            "Código de Negociação": asset.get_ticker(),
            "Data de Vencimento": asset.get_maturity_date(),
            "Emissor": asset.get_issuer(),
            "Quantidade": float(item.current_quantity),
            f"Situação em {self.current_year}": float(item.current_invested_amount),
        }

    def _set_sheet_style(self, sheet: Worksheet) -> None:
        self._set_column_number_format(sheet)
        # self._set_column_alignment(sheet)
        self._set_column_dimensions(sheet)

    def _set_column_dimensions(self, sheet: Worksheet) -> None:
        offsets = {
            "Nome": 2,
            "Instituição": 2,
            "Tipo": 1,
            "CNPJ": 1,
            "Código de Negociação": 8,
            "Data de Vencimento": 4,
            "Emissor": 2,
            "Quantidade": 8,
            f"Situação em {self.current_year}": 6,
        }
        for header, offset in offsets.items():
            column = self.get_column(header)
            length = max(len(str(cell.value)) for cell in sheet[column] if cell.row != 1)
            sheet.column_dimensions[column].width = length + offset

    def _set_column_number_format(self, sheet: Worksheet) -> None:
        number_formats = {
            f"Situação em {self.current_year}": FORMAT_CURRENCY_REAL_SIMPLE,
        }
        for header, format in number_formats.items():
            column = self.get_column(header)
            for cell in sheet[column]:
                cell.number_format = format
