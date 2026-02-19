import json
import logging
import asyncio
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class EventLogger:
    def __init__(self, storage_dir: str = "data/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file = self.storage_dir / "current_session.jsonl"
        self._lock = asyncio.Lock()

    async def log_event(self, event: Dict[str, Any]):
        """Logs an event to the append-only file."""
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()
            
        async with self._lock:
            with open(self.current_session_file, "a") as f:
                f.write(json.dumps(event) + "\n")

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Retrieves all events from the log."""
        events = []
        if not self.current_session_file.exists():
            return []
            
        with open(self.current_session_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.error("Failed to decode event line")
        return events

    def clear_log(self):
        """Clears the log (for testing or new session)."""
        if self.current_session_file.exists():
            self.current_session_file.unlink()
