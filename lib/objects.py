# Written by Jeemin Kim.
# Feb 20, 2022
# github/mrharrykim

from datetime import date
from typing import Iterable, Union

from lib.utils import TevenError, tomorrow


class RanOutOfMemberError(TevenError):
    pass

class RanOutOfGroupError(TevenError):
    pass

class DateInterval:
    """
    Properties:
        start_date: The date the interval starts, inclusive.
        end_date:   The date the interval ends, inclusive.
        person:     Person object the interval belongs to.
    """
    def __init__(self, start_date: date, end_date: date, person):
        self.start_date = start_date
        self.end_date = end_date
        self.person: Person = person

    def __len__(self) -> int:
        return self.end_date.toordinal() - self.start_date.toordinal() + 1
    
    def __repr__(self) -> str:
        return f"[{self.start_date}, {self.end_date}]"

    def contains(self, query_date: date) -> bool:
        """
        Check if given date is contained by the interval.
        """
        return self.start_date <= query_date <= self.end_date

class Person:
    """
    Properties:
        name:   Name of the person.
        group:  Group object the person is in.
        rank:   Person with higher rank is chosen first in the group.
                By higher I mean 'less' mathematically.
        count:  The number that the preson was "chosen".
                It's quoted because it increment when the person would have been chosen if they were not vacant.
                This is done so to prevent the person from being chosen more than it used to be after vacancy.
        real_count: The number that the preson was actually chosen.
        dayoffs:    List of DateInterval object representing days off.
                    The person is not chosen during day off.
        vacants:    List of DateInterval object representing vacancies.
                    The person is not chosen and not responsible for being chosen during vacancy.
    
    Arguments other than the properties:
        precount:   The number by which the person needs to be chosen more than others.
        fraction:   It determines which person is chosen first given same count.
                    It's a number between 0 and 1.
    """
    def __init__(self, name: str, group, precount: int, fraction: float, dayoffs: list[DateInterval], vacants: list[DateInterval]):
        self.name = name
        self.group: Group = group
        self.precount = precount
        self.rank = -precount + fraction
        self.count = -precount
        self.real_count = 0
        self.dayoffs = dayoffs
        self.vacants = vacants

    def __repr__(self) -> str:
        return f"{self.name}"

class Empty(Person):
    def __init__(self):
        pass
    def __repr__(self) -> str:
        return "Empty"

class Group:
    """
    Group object is a group of Person objects
    
    Properties:
        name:   Name of the group.
        pool:   LaborPool object the group is in.
        members:            List of members the group has.
        available_members:  Sublist of members that are available to be chosen.
        max_available:      Maximum number of members that can be chosen from this group.
        now_available:      The number of members available to be chosen now.
        dnw:    Delta Number of Work. The number need to be chosen to minimizie the standard deviation
                of each group's count, if so chosen. See get_count method.
        ddnw:   Discrete Delta Number of Work. The number that is going to be chosen from this group.
    """
    def __init__(self, name: str, members: list[Person], pool, max_available: int):
        self.name = name
        self.pool: LaborPool = pool
        self.members = members
        self.available_members = self.members.copy()
        self.max_available = max_available
        self.now_available = max_available
        self.dnw = 0
        self.ddnw = 0           # Discrete Delta Number of Work
        self.deviation = 0

    def get_priority_queue(self) -> list[Person]:
        """
        Get priority queue of available members based on each member's rank
        """
        self.available_members.sort(key=lambda member: member.rank)
        return self.available_members

    def get_total_priority_queue(self) -> list[Person]:
        """
        Get priority queue of members based on each member's rank
        """
        self.members.sort(key=lambda member: member.rank)
        return self.members

    def get_count(self) -> int:
        """
        Get sum of each available member's count.
        """
        return sum(map(lambda member: member.count, self.available_members))

    def get_real_count(self) -> int:
        """
        Get sum of each member's count.
        """
        return sum(map(lambda member: member.real_count, self.available_members))

    def take(self, dnw: Union[int, None], curdate: date) -> list[Person]:
        """
        Choose and get ddnw number of members from the group.

        Arguments:
            dnw:        The number of people to be chosen, if given.
            curdate:    Current date when the people is chosen.
        """
        if dnw != None:
            self.ddnw = dnw
        if self.ddnw <= 0:
            return []

        labor = []
        virtual_labor: list[Person] = []
        total_queue = self.get_total_priority_queue()
        queue = self.get_priority_queue()
        for member in total_queue:
            if any(map(lambda dayoff: dayoff.contains(curdate), member.dayoffs)):
                continue
            if any(map(lambda vacant: vacant.contains(curdate), member.vacants)):
                virtual_labor.append(member)
                member.count += 1
                member.rank += 1
            elif member not in queue:
                continue
            else:
                virtual_labor.append(member)
            if len(virtual_labor) >= self.ddnw:
                break
        for member in queue:
            labor.append(member)
            member.real_count += 1
            member.count += 1
            member.rank += 1
            member.dayoffs.append(DateInterval(tomorrow(curdate, -self.pool.gap_size), tomorrow(curdate, self.pool.gap_size), member))
            if len(labor) >= self.ddnw:
                break
        else:
            raise RanOutOfMemberError(f"Not enough member in {self.name}")
        return labor

    def __repr__(self) -> str:
        return f"Group(name=\"{self.name}\")"

class LaborPool:
    """
    LaborPool object is a group of Group objects.
    
    Properties:
        laborforces:    List of labor forces the labor pool has.
                        It's only comprised of Group objects currently.
        available_laborforces:  Sublist of laborforces that are available.
        gap_size:       The gap that a person need not to be chosen for, in day.
    """
    def __init__(self, laborforces: list[Group]):
        self.laborforces = laborforces
        self.available_laborforces = self.laborforces.copy()
        self.gap_size = 0

    def get_group(self, name: str) -> Group:
        """
        Get a group that has given name
        """
        match = filter(lambda group: group.name == name, self.laborforces)
        return next(match)

    def get_muprime(self, nwn: int) -> float:       # Number of Work, New
        """
        Get average count of available laborforces after nwn number of people is chosen.

        Arguments:
            nwn:    Number of Work, New.
        """
        return (sum(map(lambda group: group.get_count(), self.available_laborforces)) + nwn)/sum(map(lambda group: len(group.available_members), self.available_laborforces))

    def set_ddnws(self, nwn: int):
        """
        Set ddnw of each available labor force.

        Arguments:
            nwn:    Number of Work, New. It's sum of every ddnw that is set.
        """
        muprime = self.get_muprime(nwn)
        current_nwn = 0
        queue: list[Group] = []
        for group in self.available_laborforces:
            group.dnw = muprime*len(group.available_members) - group.get_count()
            if group.dnw > group.now_available:
                group.ddnw = group.now_available
            elif group.dnw < 0:
                group.ddnw = 0
                queue.append(group)
            else:
                group.ddnw = round(group.dnw)
                queue.append(group)
            current_nwn += group.ddnw

        while current_nwn != nwn:
            if not queue:
                raise RanOutOfGroupError("No more group left in the priority queue")
            queue.sort(key=lambda group: group.ddnw-group.dnw)
            if current_nwn < nwn:
                if queue[0].ddnw >= queue[0].now_available:
                    del queue[0]
                    continue
                queue[0].ddnw += 1
                current_nwn += 1
            elif current_nwn > nwn:
                if queue[-1].ddnw <= 0:
                    del queue[-1]
                    continue
                queue[-1].ddnw -= 1
                current_nwn -= 1

    def exclude(self, members: Iterable[Person], laborforces: Iterable[Group]):
        """
        Exclude given members and labor forces from available members or available labor forces respectively.
        """
        for member in members:
            if member in member.group.available_members:
                member.group.available_members.remove(member)
        for group in laborforces:
            if group in self.available_laborforces:
                self.available_laborforces.remove(group)

    def decrease(self, members: Iterable[Person]):
        """
        Decrease now available of each given member's group, by 1.
        """
        for member in members:
            member.group.now_available -= 1

    def reset(self):
        """
        Reset every available members, and available labor forces to default.
        """
        for group in self.laborforces:
            group.available_members = group.members.copy()
            group.now_available = group.max_available
        self.available_laborforces = self.laborforces.copy()

    def take(self, nwn: int, curdate: date, groups: Union[list[Group], None] = None) -> list[Person]:
        """
        Choose and get nwn number of people from labor forces.

        Arguments:
            nwn:    Number of Work, New.
            curdate:    Current date when the people is chosen.
            groups: List of Group objects that people is chosen from, if given.
        """
        if nwn <= 0:
            return labors
        if groups:
            self.available_laborforces = groups
        
        dayoff_members = map(lambda dateinterval: dateinterval.person, filter(lambda dateinterval: dateinterval.contains(curdate), self.get_dayoffs()))
        self.exclude(dayoff_members, [])
        vacant_members = map(lambda dateinterval: dateinterval.person, filter(lambda dateinterval: dateinterval.contains(curdate), self.get_vacants()))
        self.exclude(vacant_members, [])

        labors: list[Person] = []
        self.set_ddnws(nwn)
        for group in self.available_laborforces:
            labors += group.take(None, curdate)
        self.reset()
        return labors

    def get_dayoffs(self) -> list[DateInterval]:
        """
        Get every days off the labor pool has.
        """
        dayoffs = []
        for group in self.laborforces:
            for member in group.members:
                dayoffs += member.dayoffs
        return dayoffs

    def get_vacants(self) -> list[DateInterval]:
        """
        Get every vacancies the labor pool has.
        """
        vacants = []
        for group in self.laborforces:
            for member in group.members:
                vacants += member.vacants
        return vacants

    def get_counts(self, group_count: bool = True, member_count: bool = True) -> list[tuple[Union[Group, Person], int]]:
        counts: list[tuple] = []
        for group in self.laborforces:
            if group_count:
                counts.append((group, group.get_real_count()))
            if member_count:
                for member in group.members:
                    counts.append((member, member.real_count, member.precount, member.count - member.real_count + member.precount, member.count))
        return counts

    def get_size(self) -> int:
        """
        Get total number of people the labor pool has.
        """
        return sum(map(lambda group: len(group.members), self.laborforces))