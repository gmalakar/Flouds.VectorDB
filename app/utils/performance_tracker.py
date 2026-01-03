# =============================================================================
# File: performance_tracker.py
# Date: 2025-01-27
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================
import time
from contextlib import contextmanager
from typing import Dict, Optional

from app.logger import get_logger

logger = get_logger("performance_tracker")


class PerformanceTracker:
    """Tracks performance metrics for various operations."""

    def __init__(self):
        self.metrics: Dict[str, list] = {}

    @contextmanager
    def track(self, operation_name: str):
        """
        Context manager for tracking operation performance.

        Args:
            operation_name (str): Name of the operation to track

        Yields:
            None
        """
        start_time = time.time()
        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            if operation_name not in self.metrics:
                self.metrics[operation_name] = []
            self.metrics[operation_name].append(elapsed_time)

            # Log slow operations (> 100ms)
            if elapsed_time > 0.1:
                logger.debug(f"{str(operation_name)} took {elapsed_time:.3f}s")

    def get_avg(self, operation_name: str) -> float:
        """
        Get average execution time for an operation.

        Args:
            operation_name (str): Name of the operation

        Returns:
            float: Average execution time in seconds
        """
        if operation_name not in self.metrics or not self.metrics[operation_name]:
            return 0.0
        return sum(self.metrics[operation_name]) / len(self.metrics[operation_name])

    def reset(self, operation_name: Optional[str] = None):
        """
        Reset metrics for an operation or all operations.

        Args:
            operation_name (str, optional): Operation to reset. If None, resets all.
        """
        if operation_name:
            self.metrics[operation_name] = []
        else:
            self.metrics.clear()


# Global performance tracker instance
perf_tracker = PerformanceTracker()
