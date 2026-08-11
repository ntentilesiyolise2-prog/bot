from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def get_signal(self, df: pd.DataFrame) -> str:
        """Return 'BUY', 'SELL', or 'HOLD'."""
        pass
