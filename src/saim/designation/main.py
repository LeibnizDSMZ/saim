import argparse
from importlib.abc import Traversable
from pathlib import Path
import sys
from importlib import resources
import warnings

from saim.shared.error.warnings import ReadWarn
from saim.designation.known_acr_db import create_brc_con
from saim.designation.extract_ccno import identify_designation
from saim import data
from saim.shared.data_con.designation import ccno_designation_to_dict


def _parse_args(argv: list[str], /) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Takes a file with possible Culture Collection Numbers(CCNo's)"
        " and tries to decide whether those are valid CCNo's or just Designations"
    )
    parser.add_argument(
        "filename",
        nargs="?",
        default="",
        type=str,
        help="text file with ccnos or designations (1 per line)",
    )
    return parser.parse_args(argv)


def _get_file_content(filename: str, /) -> list[str]:
    lines = []
    file_path: Traversable | Path = Path(filename)
    warnings.formatwarning = lambda msg, *_arg: f"WARN: {msg}\n"
    if isinstance(file_path, Path) and not file_path.is_file():
        file_path = resources.files(data).joinpath("test_ccnos.txt")
    try:
        with file_path.open("r") as file_in:
            lines = file_in.readlines()
        if len(lines) == 0:
            warnings.warn(
                f"Failed to open file {filename!s}",
                ReadWarn,
                stacklevel=2,
            )
            sys.exit(1)
    except FileNotFoundError as fnf:
        warnings.warn(
            f"File not found {fnf!s}",
            ReadWarn,
            stacklevel=2,
        )
        sys.exit(1)
    except IOError as io:
        warnings.warn(
            f"Failed to open file {io!s}",
            ReadWarn,
            stacklevel=2,
        )
        sys.exit(1)
    return lines


def run() -> None:
    args = _parse_args(sys.argv[1:])
    brc = create_brc_con()
    brc.kn_acr.compact()
    file_content = _get_file_content(args.filename)

    for ccno in file_content:
        des_type, ccno_des = identify_designation(ccno, brc)
        des_str = "\t".join(
            [
                f"{key!s}={val!s}"
                for key, val in ccno_designation_to_dict(ccno_des).items()
            ]
        )
        print(f"{des_type.name!s} - {des_str!s}")


if __name__ == "__main__":
    run()
