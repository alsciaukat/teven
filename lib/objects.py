from lib.utils import DateInterval, TevenError

class RanOutOfMemberError(TevenError):
    pass

class NothingToIterateError(TevenError):
    pass

class Person:
    def __init__(self, name: str, dayoffs: list[DateInterval]):
        self.name = name
        self.dayoffs = dayoffs
        self.count = 0
    def __repr__(self) -> str:
        return f"Person(name=\"{self.name}\")"

def people(*names):
    return (Person(name, []) for name in names)

class Group:
    def __init__(self, name: str, members: list[Person]):
        self.name = name
        self.members = members
        self.dnw = 0
        self.idnw = 0
        self._count = 0
    def get_priority_queue(self) -> list[Person]:
        self.members.sort(key=lambda member: member.count)
        return self.members
    def get_total_count(self) -> float:
        # return sum(map(lambda member: member.count, self.members))
        return self._count
    def __repr__(self) -> str:
        return f"Group(name=\"{self.name}\")"

if __name__ == "__main__":
    a = Group(*people("harry", "lily", "jessica", "tom"))
    print(a.get_average_count())
    