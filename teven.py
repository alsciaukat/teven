# Written by Jeemin Kim.
# Feb 20, 2022
# github/mrharrykim

from typing import Union
from datetime import date
from json import load
from math import floor
import random

from lib.objects import DateInterval, Group, LaborPool, Person
from lib.utils import TevenError, isweekend, str2date, tomorrow

def max_alloc(*configs):
    """
    find maximum number of person needed per day
    """
    return max(map(lambda config: config["number_of_standby"] + config["number_of_backup"], configs))

def create_dateintervals(intervaldatas: list[Union[str, dict]], person: Person, config: dict) -> list[DateInterval]:
    """
    create DateInterval object with list of
    'string representing a date' or 'dictionary representing a interval'
    """
    intervals: list[DateInterval] = []
    if intervaldatas == None:
        return intervals
    for intervaldata in intervaldatas:
        if isinstance(intervaldata, str):
            interval_date = str2date(intervaldata, config["date_delimiter"])
            intervals.append(DateInterval(interval_date, interval_date, person))
        elif isinstance(intervaldata, dict):
            start_date = str2date(intervaldata["start"], config["date_delimiter"])
            end_date = str2date(intervaldata["end"], config["date_delimiter"])
            intervals.append(DateInterval(start_date, end_date, person))
    return intervals

def create_laborpool(groupdatas: list[dict], config: dict) -> LaborPool:
    pool = LaborPool([])
    for groupdata in groupdatas:
        group = Group(groupdata["name"], [], pool, groupdata["max_available"])
        if groupdata.get("order_by_index"):
            groupdata["members"].sort(key=lambda memberdata: memberdata["index"])
        elif config["shuffle"]:
            random.shuffle(groupdata["members"])
        for index, member in enumerate(groupdata["members"]):
            precount: int = 0
            if member.get("precount") != None:
                precount = member["precount"]
            fraction = index/len(groupdata["members"])
            person = Person(member["name"], group, precount, fraction, [], [])
            person.dayoffs = create_dateintervals(member.get("dayoffs"), person, config)
            person.vacants = create_dateintervals(member.get("vacants"), person, config)
            group.members.append(person)
        group.available_members = group.members.copy()
        pool.laborforces.append(group)
    pool.available_laborforces = pool.laborforces.copy()
    alloc = max_alloc(config["weekday"], config["weekend"])
    pool.gap_size = floor(pool.get_size()/alloc/3)
    return pool

def create_dates(month: int, weekday: bool = False, weekend: bool = False) -> list[date]:
    dates: list[date] = []
    today = date(2022, month, 1)
    while today.month == month:
        if (not isweekend(today)) and weekday:
            dates.append(today)
        if isweekend(today) and weekend:
            dates.append(today)
        today = tomorrow(today)
    return dates

def schedule(dates: list[date], pool: LaborPool, config: dict) -> list[tuple[date, list[Person], list[Person]]]:
    labors0: list[list[Person]] = []
    labors00: list[Person] = []
    start_group = pool.get_group(config["start_group"])

    labors00 += pool.take(1, dates[0], [start_group]) # Number of People Not Resolved

    pool.exclude([], [start_group])
    labors00 += pool.take(config["number_of_standby"] - 1, dates[0])

    labors0.append(labors00)

    for curdate in dates[1:]:
        labors0.append(pool.take(config["number_of_standby"], curdate))

    labors1: list[list[Person]] = []
    for curdate, labors0x in zip(dates, labors0):
        pool.exclude(labors0x, [])
        pool.decrease(labors0x)
        labors1.append(pool.take(config["number_of_backup"], curdate))
        
    return list(zip(dates, labors0, labors1))

if __name__ == "__main__":
    data: dict = load(open("data.json", "r", encoding="utf-8"))
    config = data["config"]
    period = data["period"]
    nerror = 0
    while nerror < config["retry_on_error"]:
        try:
            pool = create_laborpool(data["groups"], config)
            
            weekend_dates = create_dates(month=period["month"], weekend=True)
            weekend_schedule = schedule(weekend_dates, pool, config["weekend"])

            weekday_dates = create_dates(month=period["month"], weekday=True)
            weekday_schedule = schedule(weekday_dates, pool, config["weekday"])
        except TevenError as error:
            print(error.__class__.__name__, ": ",error)
            nerror += 1
        else:
            print(f"Retried: {nerror}")
            break
    else:
        print("Not able to make schedule")
        exit()
    monthly_schedule = weekday_schedule + weekend_schedule
    monthly_schedule.sort(key=lambda entity: entity[0])
    print(*monthly_schedule, sep="\n")
    print(*pool.get_counts(), sep="\n")