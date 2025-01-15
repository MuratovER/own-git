import hashlib
import os
import re
import zlib

from src.objects.base import GitObject
from src.objects.blob import GitBlob
from src.objects.commit import GitCommit
from src.storages.git import GitRepository


class GitService:
    def __init__(self, repository: GitRepository | None) -> None:
        if not repository:
            raise Exception("No repository was provided.")

        self.repository = repository

    def object_read(self, sha_hash) -> GitObject | None:
        """Read object sha from Git repository repo.  Return a
        GitObject whose exact type depends on the object."""

        path = self.repository.repository_file("objects", sha_hash[0:2], sha_hash[2:])

        if not os.path.isfile(path):  # type: ignore
            return None

        with open(path, "rb") as f:  # type: ignore
            constructor: type[GitObject]
            raw = zlib.decompress(f.read())

            # Read object type
            x = raw.find(b" ")
            fmt = raw[0:x]

            # Read and validate object size
            y = raw.find(b"\x00", x)
            size = int(raw[x:y].decode("ascii"))

            if size != len(raw) - y - 1:
                raise Exception(f"Malformed object {sha_hash}: bad length")

            # Pick constructor
            match fmt:
                case b"commit":
                    constructor = GitCommit
                # case b'tree'   : constructor=GitTree
                # case b'tag'    : constructor=GitTag
                case b"blob":
                    constructor = GitBlob
                case _:
                    raise Exception(
                        f"Unknown type {fmt.decode('ascii')} for object {sha_hash}"
                    )

            return constructor(raw[y + 1 :])

    def object_write(self, git_object: GitObject) -> str:
        # Serialize object data
        data = git_object.serialize()
        # Add header
        result = git_object.fmt + b" " + str(len(data)).encode() + b"\x00" + data
        # Compute hash
        sha_hash = hashlib.sha1(result).hexdigest()

        if self.repository:
            # Compute path
            path = self.repository.repository_file(
                "objects", sha_hash[0:2], sha_hash[2:], mkdir=True
            )

            if not os.path.exists(path):  # type: ignore
                with open(path, "wb") as f:  # type: ignore
                    # Compress and write
                    f.write(zlib.compress(result))
        return sha_hash

    def object_find(
        self, name: str, fmt: bytes | None = None, follow: bool = True
    ) -> str | None:
        sha_hashes = self.object_resolve(name)

        if not sha_hashes:
            raise Exception(f"No such reference {name}.")

        if len(sha_hashes) > 1:
            raise Exception(
                "Ambiguous reference {name}: Candidates are:\n - {'\n - '.join(sha)}."
            )

        sha_hash = sha_hashes[0]

        if not fmt:
            return sha_hash

        while True:
            obj = self.object_read(sha_hash)

            if not obj:
                raise Exception("There are no objects")

            if obj.fmt == fmt:
                return sha_hash

            if not follow:
                return None

            if hasattr(obj, "kvlm"):
                if obj.fmt == b"tag":
                    sha_hash = obj.kvlm[b"object"].decode("ascii")  # type: ignore
                elif obj.fmt == b"commit" and fmt == b"tree":
                    sha_hash = obj.kvlm[b"tree"].decode("ascii")  # type: ignore
                else:
                    return None

    def object_hash(self, fd, fmt: bytes) -> str | None:
        """Hash object, writing it to repo if provided."""
        git_object: GitObject
        data = fd.read()

        # Choose constructor according to fmt argument
        match fmt:
            case b"commit":
                git_object = GitCommit(data)
            # case b'tree'   : git_object=GitTree(data)
            # case b'tag'    : git_object=GitTag(data)
            case b"blob":
                git_object = GitBlob(data)
            case _:
                raise Exception(f"Unknown type {fmt.decode('utf-8')}!")

        return self.object_write(git_object)

    def object_resolve(self, name: str):
        """Resolve name to an object hash in repo.

        This function is aware of:

         - the HEAD literal
            - short and long hashes
            - tags
            - branches
            - remote branches"""
        candidates = list()
        hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

        # Empty string?  Abort.
        if not name.strip():
            return None

        # Head is nonambiguous
        if name == "HEAD":
            return [self.repository.reference_resolve("HEAD")]

        # If it's a hex string, try for a hash.
        if hashRE.match(name):
            # This may be a hash, either small or full.  4 seems to be the
            # minimal length for git to consider something a short hash.
            # This limit is documented in man git-rev-parse
            name = name.lower()
            prefix = name[0:2].encode("utf-8")
            path = self.repository.repository_dir("objects", prefix, mkdir=False)
            if path:
                rem = name[2:]
                for file in os.listdir(path):
                    if file.startswith(rem):  # type: ignore
                        candidates.append(prefix + file.decode("utf-8"))  # type: ignore

        as_tag = self.repository.reference_resolve("refs/tags/" + name)
        if as_tag:
            candidates.append(as_tag)

        as_branch = self.repository.reference_resolve("refs/heads/" + name)
        if as_branch:
            candidates.append(as_branch)

        return candidates if candidates else None
