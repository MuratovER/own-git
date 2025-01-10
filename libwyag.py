import argparse
import sys

from src.storages.git import GitRepository

argparser = argparse.ArgumentParser(description="The stupidest content tracker")

argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True


argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")

argsp.add_argument(
    "path",
    metavar="directory",
    nargs="?",
    default=".",
    help="Where to create the repository.",
)


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "init":
            GitRepository.repository_create(args.path)
        case _:
            print("Bad command.")
