import time
from typing import Any, Dict, Optional

class TTLSCache:
    def __init__(self, default_ttl: int = 60):
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self.default_ttl = default_ttl

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._data[key] = value
        self._ttl[key] = time.time() + (ttl if ttl else self.default_ttl)

    def get(self, key: str) -> Optional[Any]:
        if key in self._data:
            if self._ttl[key] > time.time():
                return self._data[key]
            else:
                del self._data[key]
                del self._ttl[key]
        return None

    def clear(self):
        self._data.clear()
        self._ttl.clear()
