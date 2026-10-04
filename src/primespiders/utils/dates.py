import datetime


def parse_date(str_date: str | None) -> datetime.date | None:
    if str_date is None:
        return None

    formats: list[str] = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    )

    for fmt in formats:
        try:
            d = datetime.datetime.strptime(str_date, fmt)
            d = d.replace(tzinfo=datetime.UTC)
            return d.date()
        except ValueError:
            continue

    return None
