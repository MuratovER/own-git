from __future__ import annotations

from abc import ABC, abstractmethod


class GitObject(ABC):
    fmt: bytes

    def __init__(self, data: bytes | None = None) -> None:
        if data:
            self.deserialize(data)
        else:
            self.init()

    @abstractmethod
    def serialize(self):
        """
        This function MUST be implemented by subclasses.
        It must read the object's contents from self.data, a byte string, and
        do whatever it takes to convert it into a meaningful representation.
        What exactly that means depend on each subclass.
        """
        raise Exception("Unimplemented!")

    @abstractmethod
    def deserialize(self, data: bytes):
        raise Exception("Unimplemented!")

    def init(self) -> None:
        pass
