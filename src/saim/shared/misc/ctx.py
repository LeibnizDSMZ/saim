import multiprocessing
from multiprocessing.context import SpawnContext
from typing import Final

from saim.shared.error.exceptions import WrongContextEx


_CTX: Final[multiprocessing.context.BaseContext] = multiprocessing.get_context("spawn")


def get_worker_ctx() -> SpawnContext:
    if not isinstance(_CTX, multiprocessing.context.SpawnContext):
        raise WrongContextEx(f"Expected SpawnContext got {type(_CTX).__name__}")
    return _CTX
