"""
SELENE OS — Worker Pool Manager
Manages the lifecycle of all execution workers. Started as a background
task on FastAPI startup. Integrates with the RecoveryManager to handle
expired leases and crashed workers.
"""

import asyncio
from typing import List
import structlog

from runtime.workers.capability_worker import CapabilityWorker
from runtime.workers.plugin_worker import PluginWorker
from runtime.workers.base_worker import BaseExecutionWorker
from runtime.recovery_manager import recovery_manager

logger = structlog.get_logger(__name__)

# Number of workers per type — keep low for alpha stability
CAPABILITY_WORKER_COUNT = 2
PLUGIN_WORKER_COUNT = 1


class WorkerPool:
    """
    Owns and manages the lifecycle of all execution workers.
    Launches workers as asyncio Tasks so they run concurrently with
    the FastAPI event loop without blocking request handling.
    """

    def __init__(self):
        self._workers: List[BaseExecutionWorker] = []
        self._tasks: List[asyncio.Task] = []
        self._recovery_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self) -> None:
        """
        Spawns all workers and the recovery manager loop.
        Called from FastAPI startup_event.
        """
        if self._is_running:
            logger.warning("worker_pool_already_running")
            return

        self._is_running = True

        # Create workers
        for _ in range(CAPABILITY_WORKER_COUNT):
            self._workers.append(CapabilityWorker())
        for _ in range(PLUGIN_WORKER_COUNT):
            self._workers.append(PluginWorker())

        # Start all workers as background tasks
        for worker in self._workers:
            task = asyncio.create_task(worker.start(), name=f"worker-{worker.worker_id}")
            self._tasks.append(task)

        # Start the recovery manager
        self._recovery_task = asyncio.create_task(
            self._recovery_loop(), name="recovery-manager"
        )

        logger.info(
            "worker_pool_started",
            capability_workers=CAPABILITY_WORKER_COUNT,
            plugin_workers=PLUGIN_WORKER_COUNT,
            total=len(self._workers),
        )

    async def stop(self) -> None:
        """
        Gracefully stops all workers and cancels background tasks.
        Called from FastAPI shutdown_event.
        """
        self._is_running = False

        # Stop all workers
        for worker in self._workers:
            await worker.stop()

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        if self._recovery_task:
            self._recovery_task.cancel()

        # Wait for clean shutdown (up to 10s)
        all_tasks = self._tasks + ([self._recovery_task] if self._recovery_task else [])
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)

        self._workers.clear()
        self._tasks.clear()
        logger.info("worker_pool_stopped")

    async def _recovery_loop(self) -> None:
        """
        Runs every 30 seconds to detect and recover expired leases.
        Dead tasks are re-enqueued up to the max retry limit.
        """
        while self._is_running:
            try:
                await asyncio.sleep(30)
                recovery_manager.recover_dead_leases()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("recovery_loop_error", error=str(e))

    @property
    def is_running(self) -> bool:
        return self._is_running

    def status(self) -> dict:
        return {
            "running": self._is_running,
            "workers": len(self._workers),
            "worker_ids": [w.worker_id for w in self._workers],
        }


# Singleton
worker_pool = WorkerPool()
