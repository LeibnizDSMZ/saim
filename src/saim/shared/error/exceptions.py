from typing import final


class KnownException(Exception):
    __slots__ = "__message"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.__message = message

    @final
    @property
    def message(self) -> str:
        return self.__message


class DesignationEx(KnownException):
    pass


class RequestURIEx(KnownException):
    pass


class WrongContextEx(KnownException):
    pass


class SessionCreationEx(KnownException):
    pass


class GlobalManagerEx(KnownException):
    pass


class StrainMatchEx(KnownException):
    pass


class ValidationEx(KnownException):
    pass
