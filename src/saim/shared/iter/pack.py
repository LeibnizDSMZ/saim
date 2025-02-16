from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator


def _pack_iter[
    T
](
    data_iter: Iterator[T],
    pkg_count: int,
    current_size: int,
    pkg_size: int,
    get_pkg_size: Callable[[T], int],
    /,
) -> Iterable[T]:
    run_size = current_size
    for _ in range(pkg_count - 1):
        if run_size >= pkg_size:
            return None
        data_el = next(data_iter, None)
        if data_el is None:
            return None
        run_size += get_pkg_size(data_el)
        yield data_el


def package_data[
    T
](
    data: Iterable[T], pkg_count: int, pkg_size: int, get_pkg_size: Callable[[T], int], /
) -> Iterable[list[T]]:
    data_iter = iter(data)
    while (fir_d := next(data_iter, None)) is not None:
        res = [fir_d]
        start_size = get_pkg_size(fir_d)
        res.extend(_pack_iter(data_iter, pkg_count, start_size, pkg_size, get_pkg_size))
        yield res
