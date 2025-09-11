from datetime import datetime, timedelta


# ---------- Helpers ----------
def start_of_day(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt):
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def parse_date(date_str, fallback=None):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y")
    except (ValueError, TypeError):
        return fallback


# ---------- Dates Logic ----------
def quarter_start_end(year, month):
    q_start_month = ((month - 1) // 3) * 3 + 1
    start = datetime(year, q_start_month, 1)
    if q_start_month + 3 > 12:
        end = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, q_start_month + 3, 1) - timedelta(days=1)
    return start_of_day(start), end_of_day(end)


class DatesManipulation:
    def __init__(self):
        self.today = datetime.now()
        self.year = self.today.year
        self.month = self.today.month

    @property
    def today_date(self):
        return start_of_day(self.today), end_of_day(self.today)

    @property
    def yesterday_date(self):
        y = self.today - timedelta(days=1)
        return start_of_day(y), end_of_day(y)

    @property
    def this_month(self):
        start = self.today.replace(day=1)
        return start_of_day(start), end_of_day(self.today)

    @property
    def last_month(self):
        last_month_end = self.today.replace(day=1) - timedelta(days=1)
        start = last_month_end.replace(day=1)
        return start_of_day(start), end_of_day(last_month_end)

    @property
    def this_finance(self):
        year = self.today.year if self.month > 3 else self.today.year - 1
        start = datetime(year, 4, 1)
        return start_of_day(start), end_of_day(self.today)

    @property
    def last_finance(self):
        year = self.today.year if self.month > 3 else self.today.year - 1
        start = datetime(year - 1, 4, 1)
        end = datetime(year, 3, 31)
        return start_of_day(start), end_of_day(end)

    @property
    def this_quarter(self):
        return quarter_start_end(self.today.year, self.today.month)

    @property
    def last_quarter(self):
        last_month = self.month - 3
        year = self.year
        if last_month <= 0:
            last_month += 12
            year -= 1
        return quarter_start_end(year, last_month)


# ---------- Main Wrapper ----------
class DatesRange:
    def __init__(self, value):
        self.dates = DatesManipulation()
        ranges = {
            "Today": self.dates.today_date,
            "Yesterday": self.dates.yesterday_date,
            "This Month": self.dates.this_month,
            "Last Month": self.dates.last_month,
            "This Finance": self.dates.this_finance,
            "Last Finance": self.dates.last_finance,
            "This Quarter": self.dates.this_quarter,
            "Last Quarter": self.dates.last_quarter,
            "Full Date": (
                start_of_day(datetime(2023, 1, 1)),
                end_of_day(self.dates.today),
            ),
        }
        self.from_date, self.to_date = ranges.get(value, self.dates.last_month)


# ---------- Public Function ----------
def getDates(request):
    today = datetime.now()
    type_of = request.GET.get("type_of", "This Month")

    if type_of == "custom":
        from_date = parse_date(request.GET.get("from_date"), today)
        to_date = parse_date(request.GET.get("to_date"), today)
        return start_of_day(from_date), end_of_day(to_date)

    date_range = DatesRange(type_of)
    return date_range.from_date, date_range.to_date
