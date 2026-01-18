# =============================================================================
# File: transaction_manager.py
# Date: 2025-01-17
# Copyright (c) 2024 Goutam Malakar. All rights reserved.
# =============================================================================

"""
Transaction manager for multi-step database operations in vector store service.

Provides context managers for transactional operations with automatic rollback
support for coordinating multiple related database operations.
"""

from contextlib import contextmanager
from typing import Any, Callable, Generator, List, Optional

from app.logger import get_logger

logger = get_logger("transaction_manager")


class TransactionOperation:
    """
    Represents a single operation within a transaction for potential rollback.

    Attributes:
        operation (Callable): The function to execute.
        args: Positional arguments for the operation.
        kwargs: Keyword arguments for the operation.
        rollback_func (Optional[Callable]): Function to call if rollback is needed.
        rollback_args: Arguments for rollback function.
        result: Result of the operation after execution.
    """

    def __init__(
        self,
        operation: Callable[..., Any],
        rollback_func: Optional[Callable[[Any], Any]] = None,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Initialize a transaction operation.

        Args:
            operation: Function to execute
            rollback_func: Function to call on rollback
            *args: Arguments for operation
            **kwargs: Keyword arguments for operation
        """
        self.operation = operation
        self.rollback_func = rollback_func
        self.args = args
        self.kwargs = kwargs
        self.result: Any = None
        self.executed = False

    def execute(self) -> Any:
        """
        Execute the operation and store the result.

        Returns:
            Result of the operation.
        """
        try:
            self.result = self.operation(*self.args, **self.kwargs)
            self.executed = True
            return self.result
        except Exception as e:
            logger.error(f"Operation failed: {e}", exc_info=True)
            raise

    def rollback(self) -> None:
        """
        Execute the rollback function if available and operation was executed.
        """
        if self.executed and self.rollback_func:
            try:
                self.rollback_func(self.result)
                logger.debug("Rollback completed successfully")
            except Exception as e:
                logger.error(f"Rollback failed: {e}", exc_info=True)


class Transaction:
    """
    Manages a sequence of database operations with rollback capability.

    Attributes:
        operations (List[TransactionOperation]): List of operations in the transaction.
        name (str): Name of the transaction for logging.
    """

    def __init__(self, name: str = "transaction"):
        """
        Initialize a transaction.

        Args:
            name: Name for the transaction (used in logging).
        """
        self.operations: List[TransactionOperation] = []
        self.name = name
        self.completed = False

    def add_operation(
        self,
        operation: Callable[..., Any],
        rollback_func: Optional[Callable[[Any], Any]] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add an operation to the transaction.

        Args:
            operation: Function to execute.
            rollback_func: Function to call on rollback.
            *args: Arguments for operation.
            **kwargs: Keyword arguments for operation.
        """
        self.operations.append(TransactionOperation(operation, rollback_func, *args, **kwargs))

    def execute(self) -> List[Any]:
        """
        Execute all operations in the transaction.

        If any operation fails, rollback previously executed operations in reverse order.

        Returns:
            List of results from all operations.

        Raises:
            Exception: The exception from the failed operation.
        """
        results = []
        try:
            for i, op in enumerate(self.operations):
                logger.debug(
                    f"Transaction '{self.name}': executing operation {i + 1}/{len(self.operations)}"
                )
                result = op.execute()
                results.append(result)

            self.completed = True
            logger.info(f"Transaction '{self.name}' completed successfully")
            return results

        except Exception:
            logger.error(f"Transaction '{self.name}' failed at operation {i + 1}, rolling back...")
            self._rollback(i)
            raise

    def _rollback(self, failed_index: int) -> None:
        """
        Rollback operations in reverse order up to the failed index.

        Args:
            failed_index: Index of the operation that failed.
        """
        # Rollback in reverse order, starting from the last successfully executed operation
        for i in range(failed_index - 1, -1, -1):
            try:
                logger.debug(f"Rolling back operation {i + 1}")
                self.operations[i].rollback()
            except Exception as e:
                logger.error(f"Error during rollback of operation {i + 1}: {e}")

    def rollback_all(self) -> None:
        """Manually rollback all executed operations in reverse order."""
        if not self.completed:
            logger.warning("Cannot rollback incomplete transaction")
            return

        logger.info(f"Manual rollback of transaction '{self.name}'")
        for i in range(len(self.operations) - 1, -1, -1):
            try:
                self.operations[i].rollback()
            except Exception as e:
                logger.error(f"Error rolling back operation {i + 1}: {e}")


@contextmanager
def transactional_operation(name: str = "transaction") -> Generator["Transaction", None, None]:
    """
    Context manager for transactional operations with automatic rollback on error.

    Usage:
        with transactional_operation("insert_and_flush") as txn:
            txn.add_operation(insert_func, rollback_delete, data)
            txn.add_operation(flush_func, rollback_unflush, collection)
            txn.execute()

    Args:
        name: Name of the transaction for logging.

    Yields:
        Transaction: Transaction object to add operations to.
    """
    txn = Transaction(name)
    try:
        yield txn
    except Exception as e:
        logger.error(f"Transaction context failed: {e}")
        raise
