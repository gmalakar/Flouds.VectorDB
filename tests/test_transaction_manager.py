import pytest

from app.modules.transaction_manager import transactional_operation, Transaction


def test_transaction_success_executes_all_operations():
    events = []

    def op1():
        events.append("op1")
        return "A"

    def op2():
        events.append("op2")
        return "B"

    with transactional_operation("success_txn") as txn:
        txn.add_operation(op1)
        txn.add_operation(op2)
        results = txn.execute()

    assert events == ["op1", "op2"]
    assert results == ["A", "B"]


def test_transaction_failure_rolls_back_in_reverse_order():
    events = []

    def op1():
        events.append("op1")
        return "A"

    def rb1(result):
        events.append(f"rb-{result}")

    def op2():
        events.append("op2")
        return "B"

    def rb2(result):
        events.append(f"rb-{result}")

    def op3():
        events.append("op3")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        with transactional_operation("failure_txn") as txn:
            txn.add_operation(op1, rb1)
            txn.add_operation(op2, rb2)
            txn.add_operation(op3)
            txn.execute()

    # Rollback should have been applied for op2 then op1
    assert events == ["op1", "op2", "op3", "rb-B", "rb-A"]
