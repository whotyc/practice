from datetime import datetime, timedelta


def parse_deadline(text: str):
    """
    Формат: YYYY-MM-DD или YYYY-MM-DD HH:MM
    """
    text = text.strip()
    try:
        if len(text) == 10:
            dt = datetime.strptime(text, "%Y-%m-%d")
            return dt
        return datetime.strptime(text, "%Y-%m-%d %H:%M")
    except:
        return None


def format_deadline(deadline_str: str | None):
    if not deadline_str:
        return "без дедлайна"
    try:
        dt = datetime.fromisoformat(deadline_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return deadline_str


def days_until(deadline_iso: str):
    dt = datetime.fromisoformat(deadline_iso)
    diff = dt - datetime.now()
    return diff.total_seconds()