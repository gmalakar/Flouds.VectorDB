from app.milvus.connection_pool import MilvusConnectionPool


class FakeClient:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_connection_pool_close_removes_all_and_calls_close():
    pool = MilvusConnectionPool()

    # Inject fake connections
    pool.connections = {
        "user@uri/default": {"client": FakeClient(), "last_used": 0, "created": 0},
        "user2@uri/default": {"client": FakeClient(), "last_used": 0, "created": 0},
    }

    clients = [info["client"] for info in pool.connections.values()]
    pool.close()

    # All connections removed and close() invoked
    assert pool.connections == {}
    assert all(c.closed for c in clients)
