# Written by Jeemin Kim.
# Feb 20, 2022
# github/mrharrykim

from argparse import ArgumentParser
from os.path import isfile
from statistics import mode
from typing import Union
from datetime import date
from json import load
from csv import writer, reader
from math import floor
import random

from lib.objects import DateInterval, Empty, Group, LaborPool, Person
from lib.utils import TevenError, isweekend, str2date, tomorrow


def max_alloc(*configs):
    """
    find maximum number of person needed per day
    """
    return max(map(lambda config: config["number_of_standby"] + config["number_of_backup"], configs))

def create_dateintervals(intervaldatas: list[Union[str, list[str]]], month: Union[int, None], person: Person, config: dict) -> list[DateInterval]:
    intervals: list[DateInterval] = []
    if intervaldatas == None:
        return intervals
    date_delimiter = config.get("date_delimiter")
    if date_delimiter == None:
        date_delimiter = "-"
    for intervaldata in intervaldatas:
        if isinstance(intervaldata, str):
            interval_date = str2date(intervaldata, month, date_delimiter)
            intervals.append(DateInterval(interval_date, interval_date, person))
        elif isinstance(intervaldata, list):
            start_date = str2date(intervaldata[0], month, date_delimiter)
            end_date = str2date(intervaldata[1], month, date_delimiter)
            intervals.append(DateInterval(start_date, end_date, person))
    return intervals

def create_laborpool(groupdatas: list[dict], period: dict, config: dict) -> LaborPool:
    pre_precounts: list[list[str]] = []
    if isfile("precounts.csv"):
        with open("precount.csv", "r", newline="", encoding="EUC-KR") as fd:
            file = reader(fd)
            for row in file:
                pre_precounts.append(row)

    pool = LaborPool([])
    if config["shuffle"]:
        random.shuffle(groupdatas)
    for groupdata in groupdatas:
        group = Group(groupdata["name"], [], pool, groupdata["max_available"])
        if groupdata.get("order_by_index"):
            groupdata["members"].sort(key=lambda memberdata: memberdata["index"])
        elif config.get("shuffle"):
            random.shuffle(groupdata["members"])
        for index, member in enumerate(groupdata["members"]):
            precount: int = 0
            for pre_precount in pre_precounts:
                if pre_precount[0] == member["name"]:
                    precount += int(pre_precount[1])
            if member.get("precount") != None:
                precount = member["precount"]
            fraction = index/len(groupdata["members"])
            person = Person(member["name"], group, precount, fraction, [], [])
            person.dayoffs = create_dateintervals(member.get("dayoffs"), period.get("month"), person, config)
            person.vacants = create_dateintervals(member.get("vacants"), period.get("month"), person, config)
            group.members.append(person)
        group.available_members = group.members.copy()
        pool.laborforces.append(group)
    pool.available_laborforces = pool.laborforces.copy()

    gap_size = config.get("date_gap_size")
    if gap_size != None and isinstance(gap_size, int) and gap_size >= 0:
        pool.gap_size = gap_size
    else:
        alloc = max_alloc(config["weekday"], config["weekend"])
        pool.gap_size = floor(pool.get_size()/alloc/3)
    return pool

def create_dates(period: dict, config: dict, weekday: bool = False, weekend: bool = False) -> list[date]:
    month = period.get("month")
    intervaldatas = period.get("days")
    dates: list[date] = []
    if intervaldatas:
        intervals = create_dateintervals(intervaldatas, month, Empty(), config)
        today = min(map(lambda interval: interval.start_date, intervals))
        end = max(map(lambda interval: interval.end_date, intervals))
        while today <= end:
            if any(map(lambda interval: interval.contains(today), intervals)):
                if (not isweekend(today)) and weekday:
                    dates.append(today)
                if isweekend(today) and weekend:
                    dates.append(today)
            today = tomorrow(today)
    else:
        today = date.today()
        if month == None:
            month = today.month
        today = date(today.year, month, 1)
        while today.month == month:
            if (not isweekend(today)) and weekday:
                dates.append(today)
            if isweekend(today) and weekend:
                dates.append(today)
            today = tomorrow(today)
    return dates

def schedule(dates: list[date], pool: LaborPool, period_config: dict) -> list[tuple[date, list[Person], list[Person]]]:
    if not dates:
        return []
    labors0: list[list[Person]] = []

    if period_config.get("start_group"):
        labors00: list[Person] = []
        start_group = pool.get_group(period_config["start_group"])
        labors00 += pool.take(1, dates[0], [start_group])

        pool.exclude([], [start_group])
        labors00 += pool.take(period_config["number_of_standby"] - 1, dates[0])
        labors0.append(labors00)

        for curdate in dates[1:]:
            labors0.append(pool.take(period_config["number_of_standby"], curdate))
    else:
        for curdate in dates:
            labors0.append(pool.take(period_config["number_of_standby"], curdate))
    labors1: list[list[Person]] = []
    for curdate, labors0x in zip(dates, labors0):
        pool.exclude(labors0x, [])
        pool.decrease(labors0x)
        labors1.append(pool.take(period_config["number_of_backup"], curdate))
        
    return list(zip(dates, labors0, labors1))


if __name__ == "__main__":
    parser = ArgumentParser(description="Workload distributer")
    parser.add_argument("-i", "--input", default="data", help="set input file name")
    parser.add_argument("-o", "--output", help="set output file name")
    parser.add_argument("-t", "--to", default="json", choices=["json", "here"], help="set to which output content goes")
    args = parser.parse_args()

    data: dict = load(open(args.input + ".json", "r", encoding="UTF-8"))
    config: dict = data["config"]
    period: dict = data.get("period")
    if period == None:
        period = {}
    nerror = 0
    maxerror = config.get("retry_on_error")
    if maxerror == None:
        maxerror = 3
    while nerror < maxerror:
        try:
            pool = create_laborpool(data["groups"], period, config)
            
            weekend_dates = create_dates(period, config, weekend=True)
            weekend_schedule = schedule(weekend_dates, pool, config["weekend"])

            weekday_dates = create_dates(period, config, weekday=True)
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
    print("Success")
    monthly_schedule = weekday_schedule + weekend_schedule
    monthly_schedule.sort(key=lambda entity: entity[0])

    counts: list[tuple[Person, int, int, int, int]] = pool.get_counts(group_count=False)
    mode_of_counts = mode(map(lambda count: count[4], counts))
    precounts = map(lambda count: (count[0].name, mode_of_counts - count[4]), counts)
    with open("_precounts.csv", "w", newline="", encoding="EUC-KR") as fd:
        file = writer(fd)
        file.writerows(precounts)

    if args.to == "json":
        output = "result"
        if config.get("output_filename"):
            output = config.get("output_filename")
        if args.output:
            output = args.output
        with open(output + ".csv", "w", newline="") as fd:
            file = writer(fd)
            fields = ["날짜", "예비"] + [""]*(config["weekday"]["number_of_standby"] - 1)
            if config["weekday"]["number_of_backup"] > 0:
                fields += ["예비대기"] + [""]*(config["weekday"]["number_of_backup"] - 1)
            file.writerow(fields)
            for daily_schedule in monthly_schedule:
                values = []
                values.append(daily_schedule[0])
                values.extend(daily_schedule[1])
                values.extend(daily_schedule[2])
                file.writerow(values)
            file.writerow([])
            file.writerow(["요약"])
            fields = ["이름", "뽑힌 횟수", "추가한 횟수", "제거된 횟수", "실질적 횟수"]
            file.writerow(fields)
            file.writerows(pool.get_counts(group_count=False))
    elif args.to == "here":
        print(*monthly_schedule, sep="\n", end="\n\n")
        print(*pool.get_counts(), sep="\n")