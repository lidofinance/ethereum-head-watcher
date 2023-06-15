from abc import ABC, abstractmethod

from unsync import unsync

from src.providers.consensus.typings import BlockHeaderFullResponse


class WatcherHandler(ABC):
    @unsync
    @abstractmethod
    def handle(self, watcher, head: BlockHeaderFullResponse):
        """
        Implement this method to handle new head.
        It will be called async and return BlockDetailsResponse.
        """
        pass  # pylint: disable=unnecessary-pass
