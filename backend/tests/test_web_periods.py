from datetime import date, timedelta

import pytest

from app.web.periods import month_before, parse_period, range_for_preset

TODAY = date(2026, 5, 15)


def test_week_preset_covers_seven_days():
    assert range_for_preset("week", TODAY) == (date(2026, 5, 9), TODAY)


def test_month_preset():
    assert range_for_preset("month", TODAY) == (date(2026, 4, 15), TODAY)


def test_quarter_preset():
    assert range_for_preset("quarter", TODAY) == (date(2026, 2, 15), TODAY)


def test_preset_defaults_to_today():
    start, end = range_for_preset("week")
    assert end == date.today()
    assert start == end - timedelta(days=6)


def test_month_before_clamps_to_end_of_month():
    assert month_before(date(2026, 3, 31), 1) == date(2026, 2, 28)
    assert month_before(date(2028, 3, 31), 1) == date(2028, 2, 29)
    assert month_before(date(2026, 5, 31), 1) == date(2026, 4, 30)


def test_month_before_crosses_year_boundary():
    assert month_before(date(2026, 1, 31), 1) == date(2025, 12, 31)
    assert month_before(date(2026, 2, 15), 3) == date(2025, 11, 15)


def test_invalid_preset_raises():
    with pytest.raises(ValueError, match="^Selecione um período válido.$"):
        range_for_preset("year", TODAY)
    with pytest.raises(ValueError, match="^Selecione um período válido.$"):
        parse_period("year", None, None)


def test_parse_period_preset_ignores_dates():
    start, end = parse_period("week", "2020-01-01", "2020-01-02")
    assert end - start == timedelta(days=6)


def test_custom_valid_range():
    assert parse_period("custom", "2026-01-01", "2026-01-31") == (
        date(2026, 1, 1),
        date(2026, 1, 31),
    )
    assert parse_period("custom", "2026-01-01", "2026-01-01") == (
        date(2026, 1, 1),
        date(2026, 1, 1),
    )


@pytest.mark.parametrize(
    ("from_value", "to_value"),
    [
        (None, None),
        ("", "2026-01-31"),
        ("2026-01-01", None),
        ("2026-01-01", ""),
        ("not-a-date", "2026-01-31"),
        ("2026-01-01", "2026-13-40"),
    ],
)
def test_custom_missing_or_invalid_dates(from_value, to_value):
    with pytest.raises(ValueError) as exc_info:
        parse_period("custom", from_value, to_value)
    assert str(exc_info.value) == "Informe as datas do período personalizado."
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_custom_start_after_end():
    with pytest.raises(ValueError) as exc_info:
        parse_period("custom", "2026-02-01", "2026-01-01")
    assert str(exc_info.value) == "A data inicial deve ser anterior à final."
