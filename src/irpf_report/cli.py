import datetime
import click
import pathlib

from irpf_report.inventory import Inventory
from irpf_report.parsers import ExcelParser, PositionReportParser, TransactionsReportParser, IRPFReportParser
from irpf_report.reports import IRPFReport

last_calendar_year = datetime.date.today().year - 1


@click.command()
@click.option(
    "-c",
    "--current",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=True,
    help="Path to the B3 positions report for the current year",
)
@click.option(
    "-p",
    "--previous",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=False,
    help="Path to the B3 positions report for the previous year (mutually exclusive with --inventory)",
)
@click.option(
    "-i",
    "--inventory",
    "irpf_report",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=False,
    help="Path to the previous year IRPF report (mutually exclusive with --previous)",
)
@click.option(
    "-t",
    "--transactions",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=False,
    help="Path to the B3 transactions report for the current year",
)
@click.option(
    "-o",
    "--output",
    default="irpf-report.xlsx",
    type=click.Path(dir_okay=False, writable=True, path_type=pathlib.Path),
    show_default=True,
    help="Path to th generated report",
)
@click.option(
    "-y",
    "--year",
    default=last_calendar_year,
    type=int,
    show_default=True,
    help="Set the target IRPF report year",
)
def main(
    current: pathlib.Path,
    output: pathlib.Path,
    year: int,
    previous: pathlib.Path | None = None,
    irpf_report: pathlib.Path | None = None,
    transactions: pathlib.Path | None = None,
) -> None:
    """Generates IRPF report spreadsheets from the B3 positions reports"""
    if previous is not None and irpf_report is not None:
        raise click.UsageError("The --previous and --inventory options are mutually exclusive, can not specify both")

    parser: ExcelParser = PositionReportParser(current)
    current_positions = parser.parse_report()

    inventory = Inventory()
    inventory.add_current_positions(current_positions)

    if previous is not None:
        parser = PositionReportParser(previous)
        previous_positions = parser.parse_report()
        inventory.add_previous_positions(previous_positions)

    if irpf_report is not None:
        parser = IRPFReportParser(irpf_report, year - 1)
        previous_positions = parser.parse_report()
        inventory.add_previous_positions(previous_positions)

    if transactions is not None:
        parser = TransactionsReportParser(transactions)
        transactions_list = parser.parse_report()
        inventory.add_transactions(transactions_list)

    report = IRPFReport(output, year)
    report.generate_report(inventory.get_investments())
