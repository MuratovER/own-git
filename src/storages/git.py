from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from _typeshed import FileDescriptorOrPath

import configparser
import os


class GitRepository:
    """A git repository"""

    worktree: str
    gitdir: str
    conf: configparser.ConfigParser

    def __init__(self, path: str, force: bool = False) -> None:
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception(f"Not a Git repositorysitory {path}")

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        config = self.repository_file("config")

        if config and os.path.exists(config):
            self.conf.read([config])  # type: ignore
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            version = int(self.conf.get("core", "repositorysitoryformatversion"))
            if version != 0:
                raise Exception(f"Unsupported repositorysitoryformatversion: {version}")

    def repository_path(self, *path) -> str:
        """Compute path under repository's gitdir."""

        if not self.gitdir:
            raise Exception("There are no repository gitdir.")

        return os.path.join(self.gitdir, *path)

    def repository_file(self, *path, mkdir=False) -> FileDescriptorOrPath | None:
        """Same as repository_path, but create dirname(*path) if absent.  For
        example, repository_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
        .git/refs/remotes/origin."""
        repository_path = None

        if self.repository_dir(*path[:-1], mkdir=mkdir):
            repository_path = self.repository_path(*path)

        return repository_path

    def repository_dir(self, *path, mkdir: bool = False) -> FileDescriptorOrPath | None:
        """Same as repository_path, but mkdir *path if absent if mkdir."""

        repository_path = self.repository_path(*path)

        if os.path.exists(repository_path):
            if os.path.isdir(repository_path):
                return repository_path
            else:
                raise Exception(f"Not a directory {path}")

        if mkdir:
            os.makedirs(repository_path)
            return repository_path
        else:
            return None

    @classmethod
    def repository_create(cls, path: str) -> GitRepository:
        """Create a new repository at path."""

        repository = GitRepository(path=path, force=True)

        # We make sure the path either doesn't exist or is an empty dir.

        if os.path.exists(repository.worktree):
            if not os.path.isdir(repository.worktree):
                raise Exception(f"{path} is not a directory!")
            if os.path.exists(repository.gitdir) and os.listdir(repository.gitdir):
                raise Exception(f"{path} is not empty!")
        else:
            os.makedirs(repository.worktree)

        assert repository.repository_dir("branches", mkdir=True)
        assert repository.repository_dir("objects", mkdir=True)
        assert repository.repository_dir("refs", "tags", mkdir=True)
        assert repository.repository_dir("refs", "heads", mkdir=True)

        # .git/description
        with open(repository.repository_file("description"), "w") as f:  # type: ignore
            f.write(
                "Unnamed repository; edit this file 'description' to name the repository.\n"
            )

        # .git/HEAD
        with open(repository.repository_file("HEAD"), "w") as f:  # type: ignore
            f.write("ref: refs/heads/master\n")

        with open(repository.repository_file("config"), "w") as f:  # type: ignore
            config = repository.repo_default_config()
            config.write(f)

        return repository

    def repo_default_config(self) -> configparser.ConfigParser:
        config = configparser.ConfigParser()

        config.add_section("core")
        config.set("core", "repositoryformatversion", "0")
        config.set("core", "filemode", "false")
        config.set("core", "bare", "false")

        return config

    @classmethod
    def repository_find(
        cls, path: str = ".", required: bool = True
    ) -> None | GitRepository:
        path = os.path.realpath(path)

        if os.path.isdir(os.path.join(path, ".git")):
            return GitRepository(path)

        parent = os.path.realpath(os.path.join(path, ".."))

        if parent == path:
            if required:
                raise Exception("No git directory.")
            else:
                return None

        return cls.repository_find(parent, required)

    def reference_resolve(self, reference: str) -> str | None:
        path = self.repository_file(reference)

        # Sometimes, an indirect reference may be broken.  This is normal
        # in one specific case: we're looking for HEAD on a new repository
        # with no commits.  In that case, .git/HEAD points to "ref:
        # refs/heads/main", but .git/refs/heads/main doesn't exist yet
        # (since there's no commit for it to refer to).
        if not os.path.isfile(path):  # type: ignore
            return None

        with open(path, "r") as fp:  # type: ignore
            data = fp.read()[:-1]
            # Drop final \n ^^^^^
        if data.startswith("ref: "):
            return self.reference_resolve(data[5:])
        else:
            return data
