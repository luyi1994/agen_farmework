from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    @abstractmethod
    def save(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def search(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def clear(self, *args, **kwargs) -> None:
        pass
