from typing import Final


class User:
    MAX_LOGIN_ATTEMPTS: Final[int] = 5

    def __init__(self, email: str) -> None:
        self.email: str = email
        self._token: str = ""
        self.__secret: str = "shh"

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.lower()

    def login(self, password: str) -> bool:
        return True

    def __eq__(self, other: object) -> bool:
        return False
