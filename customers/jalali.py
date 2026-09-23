from datetime import date


def _to_ascii_digits(value):
    return str(value).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))


def normalize_jalali_date(value):
    """Normalize and validate a Jalali date supplied by a storefront form."""
    raw = _to_ascii_digits(value or "").strip().replace("-", "/").replace(".", "/")
    parts = raw.split("/")
    if not raw:
        return ""
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("تاریخ تولد را به شکل سال/ماه/روز شمسی وارد کن.")
    year, month, day = (int(part) for part in parts)
    if year < 1200 or year > 1600 or month < 1 or month > 12 or day < 1:
        raise ValueError("تاریخ تولد شمسی معتبر نیست.")
    max_day = 31 if month <= 6 else 30
    if month == 12:
        max_day = 30
    if day > max_day:
        raise ValueError("روز واردشده برای این ماه شمسی معتبر نیست.")
    return f"{year:04d}/{month:02d}/{day:02d}"


def jalali_date_parts(gregorian_date=None):
    """Convert a Gregorian date to Jalali year, month, and day."""
    current = gregorian_date or date.today()
    gy, gm, gd = current.year, current.month, current.day
    month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + (1 if gm > 2 else 0)
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + month_days[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    jm = days // 31 + 1 if days < 186 else (days - 186) // 30 + 7
    jd = days % 31 + 1 if days < 186 else (days - 186) % 30 + 1
    return jy, jm, jd


def jalali_month_day(gregorian_date=None):
    """Convert a Gregorian date to its Jalali month/day for birthday checks."""
    _, month, day = jalali_date_parts(gregorian_date)
    return month, day
