from dataclasses import dataclass
from time import sleep
from typing import final

from keycloak import KeycloakOpenID, KeycloakPostError


@final
@dataclass(slots=True, kw_only=True, frozen=True)
class Token:
    access: str
    refresh: str


@final
class JWTCred:
    __slots__ = ("__cid", "__connection", "__name", "__pw", "__token", "__url")

    def __init__(self, user: str, pa_wd: str, cid: str, url: str, /) -> None:
        self.__name: str = user
        self.__pw: str = pa_wd
        self.__cid: str = cid
        self.__url = url

        self.__connection: KeycloakOpenID | None = None
        self.__token: Token | None = None
        super().__init__()

    def connect(self, /) -> Token:
        if self.__connection is None:
            self.__connection = KeycloakOpenID(
                server_url=self.__url, client_id=self.__cid, realm_name="dsmz"
            )
        token = self.__connection.token(self.__name, self.__pw)
        self.__token = Token(access=token["access_token"], refresh=token["refresh_token"])
        return self.__token

    @property
    def token(self) -> Token:
        if self.__token is None:
            return self.connect()
        return self.__token

    def _on_error(self, error: KeycloakPostError, /) -> None:
        err = "failed to get keycloak token:"
        err += f"\n{error.response_code!s} {error.error_message!s}"
        print(err)
        sleep(10)
        self.__connection = None
        self.__token = None
        self.refresh()

    def refresh(self) -> None:
        try:
            if self.__connection is None or self.__token is None:
                self.connect()
            else:
                token = self.__connection.refresh_token(self.__token.refresh)
                self.__token = Token(
                    access=token["access_token"], refresh=token["refresh_token"]
                )
        except KeycloakPostError as kex:
            self._on_error(kex)
