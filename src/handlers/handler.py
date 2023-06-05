from abc import ABC, abstractmethod

from unsync import unsync

from src.providers.consensus.typings import BlockDetailsResponse


class WatcherHandler(ABC):
    @unsync
    @abstractmethod
    def handle(self, watcher, head: BlockDetailsResponse):
        """
        Implement this method to handle new head.
        It will be called async and return BlockDetailsResponse.
        """
        pass  # pylint: disable=unnecessary-pass
