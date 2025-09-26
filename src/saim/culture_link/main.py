import argparse
from pathlib import Path
import sys
import warnings

from cafi.constants.versions import CURRENT_VER
from saim.culture_link.validate_file import validate_file

from saim.culture_link.validate_cafi import validate_cafi


def _parse_args(argv: list[str], /) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifies whether the current CAFI library uses correct links"
    )
    parser.add_argument(
        "-w",
        "--worker",
        action="store",
        type=int,
        required=False,
        default=1,
        help="the worker number to run concurrently",
        dest="worker",
        metavar="int",
    )
    parser.add_argument(
        "-s",
        "--db_size",
        action="store",
        type=int,
        required=False,
        default=10,
        help="the maximal size (GB) each database can have",
        dest="db_size",
        metavar="int",
    )
    parser.add_argument(
        "-i",
        "--input",
        action="store",
        type=str,
        required=False,
        default="./src/saim/data/test_links.csv",
        help="the input file containing all CCNos to verify",
        dest="input",
        metavar="str",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        type=str,
        required=False,
        default="",
        help="the output folder for the cache databases and results",
        dest="output",
        metavar="str",
    )
    parser.add_argument(
        "--cafi",
        action="store_true",
        help="whether to check CAFI database and not a file",
        dest="cafi",
    )

    return parser.parse_args(argv)


def run() -> None:
    args = _parse_args(sys.argv[1:])
    warnings.formatwarning = lambda msg, *_arg: f"WARN: {msg}\n"
    if not args.cafi and args.input != "" and (in_file := Path(args.input)).is_file():
        validate_file(
            CURRENT_VER, int(args.worker), int(args.db_size), args.output, in_file
        )
    else:
        validate_cafi(CURRENT_VER, int(args.worker), int(args.db_size), args.output)


if __name__ == "__main__":
    run()
