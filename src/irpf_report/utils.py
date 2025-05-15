from datetime import date


def format_date(date: date) -> str:
    return date.strftime("%d/%m/%Y")
