"""
SELENE OS — Distributed Execution Worker
Pulls tasks from the distributed queue, handles capabilities locally with affinity, 
and maintains lease heartbeats.
"""

import asyncio
import uuid
import structlog
from typing import List
from runtime.task_queue import task_queue
from schemas import Capability

logger = structlog.get_logger(__name__)


class BaseExecutionWorker:
    def __init__(self, supported_capabilities: List[Capability]):
        self.worker_id = f"worker_{uuid.uuid4().hex[:8]}"
        self.supported_capabilities = [c.value for c in supported_capabilities]
        self._is_running = False
        
    async def start(self):
        self._is_running = True
        logger.info("worker_started", worker_id=self.worker_id, capabilities=self.supported_capabilities)
        
        while self._is_running:
            # Poll for tasks with execution affinity for our supported capabilities
            task = task_queue.claim_task("default_tenant", self.worker_id, self.supported_capabilities)
            
            if task:
                # Spawn execution loop which handles heartbeats in the background
                await self._execute_with_heartbeat(task)
            else:
                await asyncio.sleep(1.0) # Backoff
                
    async def stop(self):
        self._is_running = False
        logger.info("worker_stopped", worker_id=self.worker_id)
        
    async def _execute_with_heartbeat(self, task: dict):
        job_id = task["job_id"]
        
        # Background task to send lease heartbeats
        async def heartbeat_loop():
            while True:
                task_queue.heartbeat(job_id)
                await asyncio.sleep(20) # Heartbeat every 20s for a 60s lease
                
        hb_task = asyncio.create_task(heartbeat_loop())
        
        try:
            logger.info("executing_task", job_id=job_id, capability=task["node"]["capability"])
            # Simulate real execution (e.g., BrowserAgent via Playwright)
            await asyncio.sleep(2.5) 
            
            # Simulated completion
            logger.info("task_completed", job_id=job_id)
            # -> Push ExecutionReceipt back to queue for Orchestrator here
            
        except Exception as e:
            logger.error("task_failed", job_id=job_id, error=str(e))
        finally:
            hb_task.cancel()
            
