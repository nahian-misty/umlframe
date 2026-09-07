class Engine:
    def __init__(self, horsepower: int) -> None:
        self.horsepower: int = horsepower


class Wheel:
    def __init__(self, size: int) -> None:
        self.size: int = size


class Person:
    def __init__(self, name: str) -> None:
        self.name: str = name


class Car:
    def __init__(self, owner: Person) -> None:
        self.engine = Engine(300)
        self.owner = owner
        self.wheels: list[Wheel] = []

    def register_owner(self, owner: Person) -> None:
        pass
