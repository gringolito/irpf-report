from collections.abc import Iterable
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.worksheet import Worksheet
import pandas
import pathlib
from typing import Any
from irpf_report.holdings import Holding


FORMAT_CURRENCY_REAL_SIMPLE = "[$R$ ]#,##0.00_-"


class AssetsReport:
    def __init__(self, file_path: pathlib.Path) -> None:
        """
        Args:
            file_path (str): The file path to the excel spreadsheet to create the report
        """
        self.path = file_path

    def generate_report(self, holdings: Iterable[Holding]) -> None:
        data = [self._format_holding(holding) for holding in holdings]
        dataframe = pandas.DataFrame(data)
        with pandas.ExcelWriter(self.path) as xls:
            dataframe.to_excel(xls, sheet_name="Bens e Direitos", header=True, index=False, float_format="%.2f")
            self._format_report(xls.sheets["Bens e Direitos"])

    def _format_holding(self, holding: Holding) -> dict[str, Any]:
        asset = holding.asset
        return {
            "Grupo": asset.get_group(),
            "Código": asset.get_code(),
            "CNPJ": asset.get_cnpj(),
            "Descrição": self._format_asset_description(holding),
            "Código de Negociação": asset.get_ticker(),
            "Situação no ano anterior": float(holding.previous_invested_amount),
            "Situação atual": float(holding.current_invested_amount),
            "Tipo": asset.get_type(),
        }

    @staticmethod
    def _format_asset_description(holding: Holding) -> str:
        asset = holding.asset
        description = asset.get_description_fmt() % holding.current_quantity

        if holding.is_closed():
            description += " - Posição encerrada em DD/MM/AAAA com lucro/prejuízo de R$ XXX,XX"

        return description

    def _format_report(self, sheet: Worksheet) -> None:
        self._set_header_style(sheet)
        self._set_column_dimensions(sheet)
        self._set_column_style(sheet)
        self._set_column_alignment(sheet)
        self._hide_internal_columns(sheet)

    @staticmethod
    def _set_header_style(sheet: Worksheet) -> None:
        header = Font(name="Helvetica", bold=True)
        center = Alignment(horizontal="center")
        for column in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            sheet[f"{column}1"].style = "Normal"
            sheet[f"{column}1"].font = header
            sheet[f"{column}1"].alignment = center

    @staticmethod
    def _set_column_dimensions(sheet: Worksheet) -> None:
        for column in ["C", "E", "F", "G", "H"]:
            length = max(len(str(cell.value)) for cell in sheet[column])
            sheet.column_dimensions[column].width = length + 2

        # Description column has too many characters, so the max length formula does fix
        length = max(len(str(cell.value)) for cell in sheet["D"])
        sheet.column_dimensions["D"].width = length - 30

    @staticmethod
    def _set_column_style(sheet: Worksheet) -> None:
        for column in ["F", "G"]:
            for cell in sheet[column]:
                cell.number_format = FORMAT_CURRENCY_REAL_SIMPLE

    @staticmethod
    def _set_column_alignment(sheet: Worksheet) -> None:
        center = Alignment(horizontal="center")
        for column in ["A", "B"]:
            for cell in sheet[column]:
                cell.alignment = center

    @staticmethod
    def _hide_internal_columns(sheet: Worksheet) -> None:
        sheet.column_dimensions["H"].hidden = True
