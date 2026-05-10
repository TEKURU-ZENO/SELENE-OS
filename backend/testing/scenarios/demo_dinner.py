import asyncio
import json
from datetime import datetime
import uuid

# Mocking the internal state for the scenario
class MockEventBus:
    def __init__(self):
        self.events = []
    
    def emit(self, event_type, payload):
        event = {
            "id": str(uuid.uuid4()),
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        self.events.append(event)
        # Print nicely for the trace
        print(f"[{event['timestamp']}] {event_type.upper()}: {json.dumps(payload, indent=2)}")

async def run_dinner_scenario():
    bus = MockEventBus()
    print("="*60)
    print("SELENE OS: Dinner Reservation Scenario Trace")
    print("="*60)

    # ── Phase 1: Observe ──────────────────────────────────────────
    bus.emit("system_state", {"message": "Parsing intent...", "status": "running"})
    await asyncio.sleep(0.5)
    bus.emit("execution_log", {"message": "Intent detected: TASK | Confidence: 0.96"})
    bus.emit("execution_log", {"message": "Inferring context: Booking context required (Time, Party Size, Location)"})

    # ── Phase 2: Plan ─────────────────────────────────────────────
    bus.emit("system_state", {"message": "Generating Hierarchical Plan...", "status": "running"})
    await asyncio.sleep(1.0)
    plan = {
        "plan_id": "plan_din_01",
        "objective": "Book dinner at Dorsia for 4 at 8 PM",
        "groups": [
            {
                "id": "g1", "objective": "Find availability",
                "nodes": [
                    {"id": "n1", "capability": "NAVIGATE_WEB", "params": {"url": "dorsia.com/reservations"}}
                ]
            },
            {
                "id": "g2", "objective": "Submit Booking",
                "nodes": [
                    {"id": "n2", "capability": "INTERACT_UI", "params": {"action": "submit_form"}}
                ]
            }
        ]
    }
    bus.emit("system_state", {"message": "Plan Generated", "plan_id": plan["plan_id"], "dag": plan})

    # ── Phase 3: Critique ─────────────────────────────────────────
    bus.emit("system_state", {"message": "Critic Evaluation", "status": "running"})
    await asyncio.sleep(0.5)
    bus.emit("execution_log", {"message": "Critic Warning: Node n2 (INTERACT_UI) is a high-risk mutation."})
    bus.emit("execution_log", {"message": "Inserting HITL Checkpoint at Node n2."})

    # ── Phase 4: Execute (With Injected Failure) ──────────────────
    bus.emit("system_state", {"message": "Executing Group g1: Find availability", "status": "running"})
    await asyncio.sleep(1.0)
    
    # Injected Failure
    bus.emit("execution_log", {"message": "BrowserAgent navigating to dorsia.com..."})
    bus.emit("execution_log", {"message": "[ERROR] TimeoutExceeded: 30000ms exceeded."})
    bus.emit("system_state", {"message": "Execution Failed. Triggering Plan Repair...", "status": "repairing"})
    
    await asyncio.sleep(1.0)
    # Repair Loop
    bus.emit("execution_log", {"message": "Critic suggests: Retry with explicit wait constraints or fallback to API."})
    bus.emit("system_state", {"message": "Retrying Node n1...", "status": "running"})
    bus.emit("execution_log", {"message": "BrowserAgent navigated successfully. Found 8 PM slot."})

    # ── Phase 5: Interrupt (HITL) ─────────────────────────────────
    bus.emit("system_state", {"message": "Awaiting Human Confirmation", "status": "halted"})
    bus.emit("interrupt", {
        "action": "Confirm reservation at Dorsia for 8:00 PM for 4 people.",
        "reason": "Policy Engine requires explicit approval for state-mutating actions (Booking).",
        "risk_level": "medium",
        "rollback_available": False
    })
    
    await asyncio.sleep(1.5)
    # Simulate User Modification
    bus.emit("execution_log", {"message": "[USER MODIFICATION] Change time to 8:30 PM."})
    bus.emit("system_state", {"message": "Resuming execution with modified parameters...", "status": "running"})
    
    await asyncio.sleep(1.0)
    bus.emit("execution_log", {"message": "Booking confirmed for 8:30 PM."})
    bus.emit("system_state", {"message": "Execution Complete.", "status": "success"})

    # ── Phase 6: Reflect ──────────────────────────────────────────
    bus.emit("system_state", {"message": "Reflection & Consolidation", "status": "running"})
    await asyncio.sleep(1.0)
    bus.emit("reflection", {
        "type": "learned",
        "pattern": "Browser navigation on Dorsia domain shows elevated latency.",
        "confidence": 0.72,
        "evidence": "1 timeout failure required repair loop retry.",
        "status": "Accepted"
    })
    bus.emit("reflection", {
        "type": "learned",
        "pattern": "User frequently modifies booking times late in the workflow.",
        "confidence": 0.85,
        "evidence": "User modified 8:00 PM to 8:30 PM at the HITL step.",
        "status": "Accepted"
    })

    print("="*60)
    print("Scenario Trace Complete. Output saved as Golden Cognitive Trace.")
    print("="*60)
    
    # Save trace to file for the artifact
    with open("golden_trace_dinner.json", "w") as f:
        json.dump(bus.events, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_dinner_scenario())
