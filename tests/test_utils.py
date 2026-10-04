import pytest

from primespiders.utils.dates import parse_date


@pytest.mark.parametrize(
    "input_date, expected_output",
    [
        ("2024-06-15", "2024-06-15"),
        ("15/06/2024", "2024-06-15"),
        ("15.06.2024", "2024-06-15"),
        ("15-06-2024", "2024-06-15"),
        ("2024/06/15", "2024-06-15"),
        (None, None),
        ("invalid-date", None),
    ]
)
def test_parse_date(input_date, expected_output):
    result = parse_date(input_date)
    if expected_output is None:
        assert result is None
    else:
        assert result.isoformat() == expected_output
