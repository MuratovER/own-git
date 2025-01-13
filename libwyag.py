import argparse
import sys

from src.services.git import GitService
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


argsp = argsubparsers.add_parser(
    "cat-file", help="Provide content of repository objects"
)

argsp.add_argument(
    "type",
    metavar="type",
    choices=["blob", "commit", "tag", "tree"],
    help="Specify the type",
)

argsp.add_argument("object", metavar="object", help="The object to display")

argsp = argsubparsers.add_parser(
    "hash-object", help="Compute object ID and optionally creates a blob from a file"
)

argsp.add_argument(
    "-t",
    metavar="type",
    dest="type",
    choices=["blob", "commit", "tag", "tree"],
    default="blob",
    help="Specify the type",
)

argsp.add_argument(
    "-w",
    dest="write",
    action="store_true",
    help="Actually write the object into the database",
)

argsp.add_argument("path", help="Read object from <file>")


def cmd_cat_file(args):
    repository = GitRepository.repository_find()

    if not repository:
        raise Exception("There are no repositories")

    git_service = GitService(repository=repository)

    git_object = git_service.object_read(git_service.object_find(args.object, fmt=None))
    if git_object:
        sys.stdout.buffer.write(git_object.serialize())


def cmd_hash_object(args):
    if args.write:
        repository = GitRepository.repository_find()
    else:
        repository = None

    git_service = GitService(repository=repository)

    with open(args.path, "rb") as fd:
        sha = git_service.object_hash(fd, args.type.encode())
        print(sha)


def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "cat-file":
            cmd_cat_file(args)
        case "hash-object":
            cmd_hash_object(args)
        case "init":
            GitRepository.repository_create(args.path)
        case _:
            print("Bad command.")
