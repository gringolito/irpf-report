import click
import pathlib
from irpf_report.parsers import PositionReportParser
from irpf_report.inventory import Inventory
from irpf_report.reports import AssetsReport


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
    "previous",
    type=click.Path(exists=True, dir_okay=False, readable=True, path_type=pathlib.Path),
    required=False,
    help="Path to the B3 positions report for the previous year",
)
@click.option(
    "-o",
    "--output",
    default="irpf-report.xlsx",
    type=click.Path(dir_okay=False, writable=True, path_type=pathlib.Path),
    show_default=True,
    help="Path to th generated report",
)
def main(current: pathlib.Path, output: pathlib.Path, previous: pathlib.Path | None = None) -> None:
    """Generates IRPF report spreadsheets from the B3 positions reports"""
    parser = PositionReportParser(current)
    current_positions = parser.parse_report()

    previous_positions = None
    if previous is not None:
        parser = PositionReportParser(previous)
        previous_positions = parser.parse_report()

    inventory = Inventory(current_positions, previous_positions)

    report = AssetsReport(output)
    report.generate_report(inventory.get_holdings())
