from datetime import date
from json import load
from math import floor

from lib.objects import Group, Person

def create_groups(groupdata: list[dict]) -> list[Group]:
    groups: list[Group] = []
    for group in groupdata:
        members: list[Person] = []
        for member in group["members"]:
            members.append(Person(member["name"], []))
        groups.append(Group(group["name"], members))
    return groups

def isweekend(query_date: date) -> bool:
    return query_date.isoweekday() == 6 or query_date.isoweekday() == 7

def tomorrow(query_date: date) -> date:
    return date.fromordinal(query_date.toordinal() + 1)


# for member in self.get_priority_queue():
#     if any(map(lambda dayoff: dayoff.contains(current_date), member.dayoffs)):
#         continue
#     next_member = member
#     break

if __name__ == "__main__":
    groupdata: list[dict] = load(open("groupdata.json", "r", encoding="utf-8"))
    groups = create_groups(groupdata)
    current_date = date(2022, 2, 1)
    nwn = 2
    while current_date.month == 2:
        if isweekend(current_date):
            muprime = (sum(map(lambda group: group.get_total_count(), groups)) + nwn)/sum(map(lambda group: len(group.members), groups))
            for group in groups:
                group.dnw = muprime*len(group.members)-group.get_total_count()
            groups.sort(key=lambda group: group.dnw)
            current_nwn = 0
            for group in groups:
                fdnw = floor(group.dnw)
                group.dnw -= fdnw
                group.idnw = fdnw
                group._count += fdnw
                current_nwn += fdnw
            while current_nwn < nwn:
                largest_group = max(groups, key=lambda group: group.dnw)
                largest_group.idnw += 1
                largest_group._count += 1
                current_nwn += 1
                largest_group.dnw = 0
            print(current_date, [group.name + str(group.idnw) for group in groups])
        current_date = tomorrow(current_date)

                
            






    

    

