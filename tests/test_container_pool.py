import asyncio
import contextlib

import pytest

from tests.conftest import make_mock_container


class TestStartup:
    @pytest.mark.asyncio
    async def test_prewarms_pool_size_containers(self, pool, mock_docker, pool_settings):
        await pool.startup()

        assert mock_docker.containers.create.call_count == pool_settings.exec_pool_size
        assert pool._idle.qsize() == pool_settings.exec_pool_size

    @pytest.mark.asyncio
    async def test_partial_failure_still_starts_successful_containers(
        self, pool, mock_docker, pool_settings
    ):
        good = make_mock_container()
        mock_docker.containers.create.side_effect = [good, Exception("Docker unavailable")]

        await pool.startup()

        assert pool._idle.qsize() == 1

    @pytest.mark.asyncio
    async def test_all_failures_starts_empty_pool(self, pool, mock_docker):
        mock_docker.containers.create.side_effect = Exception("no Docker")

        await pool.startup()

        assert pool._idle.empty()

    @pytest.mark.asyncio
    async def test_exec_prefix_loaded_from_image_labels(self, pool, mock_docker):
        mock_docker.images.get.return_value = {
            "Config": {"Labels": {"lang.exec": "python3 -u"}}
        }

        await pool.startup()

        assert pool._exec_prefix == ["python3", "-u"]

    @pytest.mark.asyncio
    async def test_exec_prefix_empty_when_no_label(self, pool, mock_docker):
        mock_docker.images.get.return_value = {"Config": {"Labels": {}}}

        await pool.startup()

        assert pool._exec_prefix == []

    @pytest.mark.asyncio
    async def test_exec_prefix_empty_when_no_config(self, pool, mock_docker):
        mock_docker.images.get.return_value = {}

        await pool.startup()

        assert pool._exec_prefix == []


class TestAcquire:
    @pytest.mark.asyncio
    async def test_acquire_returns_idle_container_without_creating(
        self, pool, mock_docker, pool_settings
    ):
        c1 = make_mock_container()
        c2 = make_mock_container()
        pool._idle.put_nowait(c1)
        pool._idle.put_nowait(c2)
        mock_docker.containers.create.reset_mock()

        result = await pool.acquire()

        assert result is c1
        mock_docker.containers.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_acquire_creates_container_when_queue_empty(self, pool, mock_docker):
        new_container = make_mock_container()
        mock_docker.containers.create.side_effect = [new_container]

        result = await pool.acquire()

        assert result is new_container
        mock_docker.containers.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_acquire_drains_queue_fifo(self, pool, pool_settings):
        containers = [make_mock_container() for _ in range(pool_settings.exec_pool_size)]
        for c in containers:
            pool._idle.put_nowait(c)

        results = [await pool.acquire() for _ in range(pool_settings.exec_pool_size)]

        assert results == containers


class TestSynchronization:
    @pytest.mark.asyncio
    async def test_semaphore_blocks_beyond_pool_plus_overflow(self, pool, pool_settings):
        total = pool_settings.exec_pool_size + pool_settings.exec_pool_overflow  # 3

        # Exhaust all semaphore slots
        _held = [await pool.acquire() for _ in range(total)]

        # Next acquire must block
        blocked = asyncio.create_task(pool.acquire())
        await asyncio.sleep(0)
        assert not blocked.done()

        blocked.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await blocked

    @pytest.mark.asyncio
    async def test_release_unblocks_waiting_acquire(self, pool, mock_docker, pool_settings):
        total = pool_settings.exec_pool_size + pool_settings.exec_pool_overflow  # 3
        held = [await pool.acquire() for _ in range(total)]

        blocked = asyncio.create_task(pool.acquire())
        await asyncio.sleep(0)
        assert not blocked.done()

        # Release one slot; semaphore is freed synchronously before the background task runs
        await pool.release(held[0])
        result = await asyncio.wait_for(blocked, timeout=1.0)

        assert result is not None

    @pytest.mark.asyncio
    async def test_release_restores_semaphore_immediately(self, pool, pool_settings):
        container = await pool.acquire()

        before = pool._semaphore._value
        await pool.release(container)
        after = pool._semaphore._value

        assert after == before + 1

    @pytest.mark.asyncio
    async def test_concurrent_acquires_all_succeed_within_limit(self, pool, pool_settings):
        total = pool_settings.exec_pool_size + pool_settings.exec_pool_overflow  # 3

        tasks = [asyncio.create_task(pool.acquire()) for _ in range(total)]
        results = await asyncio.gather(*tasks)

        assert len(results) == total
        assert all(r is not None for r in results)


class TestRetireAndReplenish:
    @pytest.mark.asyncio
    async def test_always_deletes_old_container_on_success(self, pool, mock_docker):
        old = make_mock_container()
        new = make_mock_container()
        mock_docker.containers.create.side_effect = [new]

        await pool._retire_and_replenish(old)

        old.delete.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_always_deletes_old_container_when_create_fails(self, pool, mock_docker):
        old = make_mock_container()
        mock_docker.containers.create.side_effect = Exception("out of resources")

        await pool._retire_and_replenish(old)

        old.delete.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_deletes_new_container_when_queue_fills_during_create(
        self, pool, mock_docker, pool_settings
    ):
        # Race condition: queue is empty when the full-check runs, but fills up
        # while _create is awaited. The put_nowait then raises QueueFull and
        # the pool must delete the freshly-created container to avoid leaking it.
        old = make_mock_container()
        new = make_mock_container()

        async def slow_create(_):
            await asyncio.sleep(0)  # yield so the queue can be filled
            return new

        mock_docker.containers.create.side_effect = slow_create

        replenish_task = asyncio.create_task(pool._retire_and_replenish(old))

        # After _retire_and_replenish passes the empty-queue check but before
        # _create returns, fill the queue to capacity.
        await asyncio.sleep(0)
        for _ in range(pool_settings.exec_pool_size):
            pool._idle.put_nowait(make_mock_container())

        await replenish_task

        new.delete.assert_called_once_with(force=True)

    @pytest.mark.asyncio
    async def test_adds_new_container_to_queue_when_not_full(self, pool, mock_docker):
        old = make_mock_container()
        new = make_mock_container()
        mock_docker.containers.create.side_effect = [new]

        assert pool._idle.empty()
        await pool._retire_and_replenish(old)

        assert pool._idle.qsize() == 1
        assert pool._idle.get_nowait() is new

    @pytest.mark.asyncio
    async def test_does_not_replenish_when_queue_already_full(self, pool, mock_docker, pool_settings):
        old = make_mock_container()
        for _ in range(pool_settings.exec_pool_size):
            pool._idle.put_nowait(make_mock_container())
        mock_docker.containers.create.reset_mock()

        await pool._retire_and_replenish(old)

        mock_docker.containers.create.assert_not_called()


class TestDeleteSafely:
    @pytest.mark.asyncio
    async def test_suppresses_exception_on_delete_failure(self, pool):
        bad_container = make_mock_container()
        bad_container.delete.side_effect = Exception("connection refused")

        await pool._delete_safely(bad_container)  # must not raise

    @pytest.mark.asyncio
    async def test_calls_delete_with_force(self, pool):
        container = make_mock_container()

        await pool._delete_safely(container)

        container.delete.assert_called_once_with(force=True)


class TestShutdown:
    @pytest.mark.asyncio
    async def test_deletes_all_idle_containers(self, pool):
        c1 = make_mock_container()
        c2 = make_mock_container()
        pool._idle.put_nowait(c1)
        pool._idle.put_nowait(c2)

        await pool.shutdown()

        c1.delete.assert_called_once_with(force=True)
        c2.delete.assert_called_once_with(force=True)
        assert pool._idle.empty()

    @pytest.mark.asyncio
    async def test_shutdown_empty_pool_is_safe(self, pool):
        await pool.shutdown()  # must not raise


class TestBuildExecCmd:
    def test_combines_prefix_with_file_path(self, pool):
        pool._exec_prefix = ["python3", "-u"]

        result = pool.build_exec_cmd("/media/code/script.py")

        assert result == ["python3", "-u", "/media/code/script.py"]

    def test_empty_prefix_returns_only_file_path(self, pool):
        pool._exec_prefix = []

        result = pool.build_exec_cmd("/media/code/script.py")

        assert result == ["/media/code/script.py"]
