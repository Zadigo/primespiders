import datetime

import pytz


def parse_date(str_date: str | None) -> datetime.date | None:
    if str_date is None:
        return None

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
        "%d.%m.%y",
    )

    for fmt in formats:
        try:
            d = datetime.datetime.strptime(str_date, fmt)
        except ValueError:
            continue
        else:
            d = d.replace(tzinfo=pytz.timezone('Europe/Paris'))
            return d.date()

    return None
