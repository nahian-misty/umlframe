class Animal:
    def __init__(self, name: str) -> None:
        self.name: str = name

    def speak(self) -> str:
        return ""


class Dog(Animal, UnknownMixin):
    def bark(self) -> str:
        return "Woof"
