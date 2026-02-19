import asyncio
import logging
import json
from typing import Dict, Any, Type, Optional
from grok_team.event_bus import EventBus
from grok_team.actor import Actor
from grok_team.config import ALL_AGENT_NAMES
from grok_team.event_logger import EventLogger

logger = logging.getLogger(__name__)

class Kernel:
    def __init__(self):
        self.event_bus = EventBus()
        self.actors: Dict[str, Actor] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        self.tool_history: Dict[str, list] = {}
        self.event_logger = EventLogger()

    def register_actor(self, actor: Actor):
        self.actors[actor.name] = actor

    async def start(self):
        self.running = True
        logger.info("Kernel starting...")
        
        # Subscribe to System Calls and Tool Use
        self.event_bus.subscribe("SystemCall", self._handle_system_call)
        self.event_bus.subscribe("ToolUse", self._handle_tool_use)
        
        # Subscribe Logger to EVERYTHING (Mocking wildcard by explicit sub or modifying EventBus)
        # Since EventBus simple implementation doesn't support wildcards yet,
        # we will modify EventBus or just subscribe to known types.
        # Ideally, EventBus should have a 'spy' or 'global' subscriber.
        # Let's add a global listener to EventBus in next step. For now, subscribe to known types.
        # Or better: MODIFY Event Bus to support global subscribers.
        # For this step, I will add `subscribe_all` to EventBus.
        
        # Assuming EventBus update is coming, I will use a private method or update EventBus first.
        # Let's stick to modifying EventBus in next step.
        # For now, I'll assume I can attach it.
        self.event_bus.subscribe_globally(self._handle_global_logging)

        # Start all registered actors
        for name, actor in self.actors.items():
            self._spawn_actor_task(actor)
            
    async def _handle_global_logging(self, event: Dict[str, Any]):
        await self.event_logger.log_event(event)

    async def _handle_tool_use(self, event: Dict[str, Any]):
        """Monitors tool usage for loops."""
        actor_name = event.get("actor")
        tool_name = event.get("tool")
        args = event.get("args")
        
        # Simple Loop Detection: 3 identical calls in a row
        history = self.tool_history.setdefault(actor_name, [])
        
        # Store simplified signature
        call_sig = (tool_name, json.dumps(args, sort_keys=True))
        history.append(call_sig)
        
        # Keep last 10
        if len(history) > 10:
            history.pop(0)
            
        # Check last 3
        if len(history) >= 3:
            if history[-1] == history[-2] == history[-3]:
                logger.warning(f"Loop detected for {actor_name}: {tool_name} called 3 times with same args.")
                await self.interrupt_agent(actor_name, f"Loop Detected: You are repeating {tool_name} with same arguments. Stop.")
                # Clear history to avoid continuous interruption?
                self.tool_history[actor_name] = []

    async def _handle_system_call(self, event: Dict[str, Any]):
        """Processes system calls from agents."""
        command = event.get("command")
        args = event.get("args", {})
        sender = event.get("sender")
        tool_id = event.get("tool_call_id")

        logger.info(f"Kernel handling system call '{command}' from {sender}")
        
        result = "Unknown command"
        
        if command == "spawn_agent":
            name = args.get("name")
            role = args.get("system_prompt") 
            temp = args.get("temperature", 0.7)
            # In real dynamic spawning, we'd need to dynamically create the class or instance
            # For now, we reuse the base Agent class
            from grok_team.agent import Agent
            success, msg = await self.spawn_agent(name, role, Agent, temperature=temp)
            result = msg
            
        elif command == "kill_agent":
            name = args.get("name")
            success, msg = await self.kill_agent(name)
            result = msg
            
        elif command == "list_agents":
            result = json.dumps(list(self.actors.keys())) # JSON string for tool output

        elif command == "allocate_budget":
            target_agent = args.get("agent_name")
            amount = args.get("amount")
            if target_agent in self.actors:
                await self.actors[target_agent].inbox.put({
                    "type": "BudgetUpdate",
                    "amount": amount
                })
                result = f"Allocated {amount} budget to {target_agent}"
            else:
                result = f"Agent {target_agent} not found"

        # Send result back
        if sender:
             await self.event_bus.publish({
                 "type": "SystemCallResult",
                 "target": sender,
                 "content": result,
                 "tool_call_id": tool_id
             })

    async def stop(self):
        self.running = False
        logger.info("Kernel stopping...")
        for name, actor in self.actors.items():
            actor.stop()
        
        if self.tasks:
            await asyncio.gather(*self.tasks.values(), return_exceptions=True)

    def _spawn_actor_task(self, actor: Actor):
        task = asyncio.create_task(actor.start(), name=f"ActorTask-{actor.name}")
        self.tasks[actor.name] = task
        task.add_done_callback(lambda t: self._handle_actor_exit(actor.name, t))
        logger.info(f"Kernel spawned process for actor '{actor.name}'.")

    def _handle_actor_exit(self, name: str, task: asyncio.Task):
        """Zombie Reaper logic."""
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Zombie Reaper: Actor '{name}' crashed with error: {exc}")
                # Publish ActorCrashed event
                asyncio.create_task(self.event_bus.publish({
                    "type": "ActorCrashed",
                    "actor": name,
                    "error": str(exc),
                    "target": "Grok" # Notify Leader? Or a system supervisor?
                }))
            else:
                logger.info(f"Actor '{name}' exited normally.")
        except asyncio.CancelledError:
            logger.info(f"Actor '{name}' was cancelled.")

    # --- System Calls for Leader ---

    async def spawn_agent(self, name: str, system_prompt: str, agent_cls=None, **kwargs):
        if name in self.actors:
            return False, "Agent already exists"
            
        if agent_cls is None:
             from grok_team.agent import Agent
             agent_cls = Agent

        new_agent = agent_cls(name, self.event_bus, system_prompt=system_prompt, **kwargs)  # Create instance
        self.register_actor(new_agent)
        self._spawn_actor_task(new_agent)
        
        # Publish Event
        await self.event_bus.publish({
            "type": "AgentSpawned",
            "actor": name,
            "from": "Kernel",
            "system_prompt": system_prompt
        })
        
        return True, "Spawned"

    async def interrupt_agent(self, name: str, reason: str = None):
        if name in self.actors:
            payload = {"type": "InterruptSignal"}
            if reason:
                payload["content"] = reason
            await self.actors[name].inbox.put(payload)
            return True, "Interrupted"
        return False, "Agent not found"

    async def kill_agent(self, name: str):
        if name in self.tasks:
            task = self.tasks[name]
            task.cancel()
            
            await self.event_bus.publish({
                "type": "AgentStopped",
                "actor": name,
                "from": "Kernel",
                "reason": "Killed by User/System"
            })
            
            return True, "Killed"
        return False, "Agent not found"

    async def recover_session(self):
        """Reconstructs state from the event log."""
        logger.info("Recovering session from event log...")
        events = self.event_logger.get_all_events()
        if not events:
            logger.info("No events found. Starting fresh.")
            return

        # Clear current state (if any)
        # self.stop() # Should be called before
        self.actors.clear()
        
        # We need to replay "structural" events first to ensure actors exist?
        # Or just replay in order.
        
        for event in events:
            etype = event.get("type")
            
            if etype == "SystemCall":
                # Check for spawn
                cmd = event.get("command")
                if cmd == "spawn_agent":
                    args = event.get("args", {})
                    name = args.get("name")
                    prompt = args.get("system_prompt")
                    temp = args.get("temperature", 0.7)
                    if name and name not in self.actors:
                        from grok_team.agent import Agent
                        # We spawn but maybe NOT start the task yet? Or start it.
                        await self.spawn_agent(name, prompt, Agent, temperature=temp)
                        
            elif etype == "TaskSubmitted":
                # User sent message to Agent
                target = event.get("target") # or is it routed via 'to'? 
                # Wait, TaskSubmitted usually has 'target' (inbox) or handled by someone.
                # In `handle_message`: "TaskSubmitted" content is archived as "user" message.
                # We need to manually append to agent's memory if we want to restore state.
                sender = event.get("from", "User")
                content = event.get("content")
                
                # We need to know who received it. The event bus routing logic uses 'target'.
                # But `TaskSubmitted` might be broadcast.
                # Let's assume we can inhibit the *logic* triggering if we are recovering.
                # The Actors are running! If we send them messages, they will REACT.
                # We do NOT want them to react during recovery. 
                # We just want to fill their state.
                
                # CRITICAL: We need a way to silent-load state.
                # Access actors directly.
                target_actor = event.get("target") # Currently our events might not have 'target' if broadcast?
                # Usage: sender sends TaskSubmitted. 
                # If we modify Agent to expose `restore_message`...
                pass # Complex to fully replay without side effects without refactoring Agent.
                
                # MVP Strategy:
                # 1. Re-spawn agents.
                # 2. We skip message replay for now in this iteration unless we refactor Agent to support "hydration".
                #    Ideally, Agent state snapshots should be logged.
                #    Event Sourcing usually requires "apply" methods.
                
        logger.info("Session recovery: Agents respawned (MVP). Full state restoration requires Agent hydration.")
