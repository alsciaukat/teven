from datetime import date

class TevenError(Exception):
    pass

class DateInterval:
    def __init__(self, start_date: date, end_date: date):
        self.start_date = start_date
        self.end_date = end_date
    def contains(self, query_date: date) -> bool:
        return self.start_date <= query_date <= self.end_date

if __name__ == "__main__":
    i = DateInterval(date(2022, 2, 17), date(2022, 3, 1))
    print(i.contains(date(2022, 2, 20)))