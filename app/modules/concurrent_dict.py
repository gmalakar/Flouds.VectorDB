# =============================================================================
# File: concurrent_dict.py
# Date: 2025-06-10
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

import threading
from typing import Any, Callable, Dict, Optional


class ConcurrentDict:
    """
    Thread-safe dictionary for concurrent access.
    Provides atomic get, set, remove, and get_or_add operations.

    Attributes:
        _lock (threading.Lock): Lock for thread safety.
        _dict (dict): Internal dictionary storage.
        _created_for (Any): Optional metadata for the dictionary.
    """

    _lock: threading.Lock
    _dict: Dict[Any, Any]
    _created_for: Any

    def __init__(self, created_for: Any = None):
        self._lock = threading.Lock()
        self._dict = {}
        self._created_for = created_for

    @property
    def created_for(self) -> Any:
        """
        Get the 'created_for' attribute.

        Returns:
            Any: The value of the 'created_for' attribute.
        """
        return self._created_for

    @created_for.setter
    def created_for(self, value: Any) -> None:
        """
        Set the 'created_for' attribute.

        Args:
            value (Any): The value to set for 'created_for'.
        """
        self._created_for = value

    def get(self, key: Any, default: Optional[Any] = None) -> Any:
        """
        Thread-safe get operation.

        Args:
            key (Any): The key to retrieve.
            default (Optional[Any], optional): Default value if key is not found. Defaults to None.

        Returns:
            Any: The value for the key, or default if not found.
        """
        with self._lock:
            return self._dict.get(key, default)

    def set(self, key: Any, value: Any) -> None:
        """
        Thread-safe set operation.

        Args:
            key (Any): The key to set.
            value (Any): The value to set for the key.
        """
        with self._lock:
            self._dict[key] = value

    def remove(self, key: Any) -> None:
        """
        Thread-safe remove operation.

        Args:
            key (Any): The key to remove from the dictionary.
        """
        with self._lock:
            if key in self._dict:
                del self._dict[key]

    def get_or_add(self, key: Any, factory: Callable[[], Any]) -> Any:
        """
        Atomically get the value for the key, or add it using the factory if not present.

        Args:
            key (Any): The key to retrieve or add.
            factory (Callable[[], Any]): Factory function to create the value if key is missing.

        Returns:
            Any: The value for the key.
        """
        with self._lock:
            if key in self._dict:
                return self._dict[key]
            value = factory()
            self._dict[key] = value
            return value

    def is_empty(self) -> bool:
        """Thread-safe check if the dictionary is empty.

        Returns:
            bool: True if the dictionary is empty, False otherwise.
        """
        with self._lock:
            return len(self._dict) == 0

    @staticmethod
    def add_missing_from_other(
        target: "ConcurrentDict", source: "ConcurrentDict"
    ) -> "ConcurrentDict":
        """
        Thread-safe: Add only missing key-value pairs from source to target ConcurrentDict.
        If target is None, creates a new ConcurrentDict and copies all items from source.
        Existing keys in target are not overwritten.

        Args:
            target (ConcurrentDict): The target dictionary to update (or None to create new).
            source (ConcurrentDict): The source dictionary to copy from.

        Returns:
            ConcurrentDict: The updated target ConcurrentDict.

        Raises:
            TypeError: If arguments are not ConcurrentDict instances.
        """
        if not isinstance(target, ConcurrentDict) and target is not None:
            raise TypeError("target must be a ConcurrentDict or None")
        if not isinstance(source, ConcurrentDict):
            raise TypeError("source must be a ConcurrentDict")
        if target is None:
            target = ConcurrentDict()
        with target._lock, source._lock:
            for key, value in source._dict.items():
                if key not in target._dict:
                    target._dict[key] = value
        return target
