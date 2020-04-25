from abc import ABC
from typing import List, Callable, Optional, Iterable


class Action:

    __slots__ = ('package',)

    def __init__(self, package):
        self.package = package

    def execute(self):
        raise NotImplementedError("")


class LoggingInstalledFilesAction(Action, ABC):

    def sources_installed(self) -> Iterable[str]:
        raise NotImplementedError("")


class InstallFiles(Action):

    __slots__ = ('sources', 'into')

    def __init__(self, package, sources: List[str], into: str):
        super().__init__(package)
        self.sources = sources
        self.into = into

    def sources_installed(self) -> Iterable[str]:
        return self.sources


class InstallAs(Action):

    __slots__ = ('source', 'dest')

    def __init__(self, package, source: str, dest: str):
        super().__init__(package)
        self.source = source
        self.dest = dest

    def sources_installed(self) -> Iterable[str]:
        yield self.source


class CreateSymlink(Action):

    __slots__ = ('source', 'dest')

    def __init__(self, package, source: str, dest: str):
        super().__init__(package)
        self.source = source
        self.dest = dest


class ConditionalAction(Action):

    __slots__ = ('conditional', 'if_true', 'if_false')

    def __init__(self, package, conditional: Callable[[], bool], if_true: Action, if_false: Optional[Action] = None):
        super().__init__(package)
        self.conditional = conditional
        assert self.if_true.package == package
        assert self.if_false is None or self.if_false.package == package
        self.if_true = if_true
        self.if_false = if_false

    def execute(self):
        if self.conditional():
            return self.if_true.execute()
        if self.if_false:
            return self.if_false.execute()
