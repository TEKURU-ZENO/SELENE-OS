"""
SELENE OS — Artifact Mapper
Maps raw external data dumps into governed ArtifactRef objects, keeping the
cognitive stream clean of heavy binaries or raw text dumps.
"""

import hashlib
import uuid
from typing import Optional
from schemas import ArtifactRef, ArtifactSensitivity, ReplayFidelity

class ArtifactMapper:
    
    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def create_artifact_ref(
        self, 
        name: str, 
        content: bytes, 
        sensitivity: ArtifactSensitivity,
        fidelity: ReplayFidelity,
        uri: Optional[str] = None
    ) -> ArtifactRef:
        """
        Creates a reference without injecting the massive raw content into memory.
        In practice, the content is saved to disk/S3 and the URI is returned.
        """
        content_hash = self._hash_content(content)
        size_bytes = len(content)
        
        return ArtifactRef(
            id=str(uuid.uuid4()),
            name=name,
            sensitivity=sensitivity,
            replay_fidelity=fidelity,
            hash=content_hash,
            size_bytes=size_bytes,
            uri=uri
        )

artifact_mapper = ArtifactMapper()
