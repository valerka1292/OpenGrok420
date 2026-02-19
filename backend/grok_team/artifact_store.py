from typing import Dict, Optional
import uuid

class ArtifactStore:
    def __init__(self):
        self._store: Dict[str, str] = {}

    def store(self, content: str) -> str:
        """Stores content and returns a unique ID."""
        artifact_id = str(uuid.uuid4())
        self._store[artifact_id] = content
        return artifact_id

    def retrieve(self, artifact_id: str, start: int = 0, length: int = 4000) -> Optional[str]:
        """Retrieves a chunk of the artifact content."""
        content = self._store.get(artifact_id)
        if content is None:
            return None
        
        if start >= len(content):
            return ""
            
        return content[start : start + length]

    def get_metadata(self, artifact_id: str) -> Optional[Dict]:
        content = self._store.get(artifact_id)
        if content is None:
            return None
        return {
            "size": len(content),
            "id": artifact_id
        }

# Global instance for current process
GLOBAL_ARTIFACT_STORE = ArtifactStore()
