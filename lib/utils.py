# Written by Jeemin Kim.
# Feb 20, 2022
# github/mrharrykim

from datetime import date


class TevenError(Exception):
    pass

class NotValidDateError(TevenError):
    pass

def isweekend(query_date: date) -> bool:
    return query_date.isoweekday() == 6 or query_date.isoweekday() == 7

def tomorrow(query_date: date, days: int = 1) -> date:
    return date.fromordinal(query_date.toordinal() + days)

def str2date(string: str, month: int = None, delimiter: str = "-") -> date:
    components = tuple(map(lambda s: int(s), string.split(delimiter)))
    today = date.today()
    if len(components) == 2:
        return date(today.year, components[0], components[1])
    if len(components) == 1:
        if month != None:
            return date(today.year, month, components[0])
        return date(today.year, today.month + 1, components[0])
    if len(components == 3):
        return date(components[0], components[1], components[2])
    raise NotValidDateError(f"'{string}' is not a valid date format")