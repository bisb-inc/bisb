from calendar import monthrange
from datetime import date, timedelta


def month_before(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, month = divmod(month_index, 12)
    month += 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def range_for_preset(preset: str, today: date | None = None) -> tuple[date, date]:
    end = today or date.today()
    if preset == "week":
        start = end - timedelta(days=6)
    elif preset == "month":
        start = month_before(end, 1)
    elif preset == "quarter":
        start = month_before(end, 3)
    else:
        raise ValueError("Selecione um período válido.")
    return start, end


def parse_period(preset: str, from_value: str | None, to_value: str | None) -> tuple[date, date]:
    if preset != "custom":
        return range_for_preset(preset)
    try:
        start = date.fromisoformat(from_value or "")
        end = date.fromisoformat(to_value or "")
    except ValueError as exc:
        raise ValueError("Informe as datas do período personalizado.") from exc
    if start > end:
        raise ValueError("A data inicial deve ser anterior à final.")
    return start, end
