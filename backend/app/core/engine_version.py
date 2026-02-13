import hashlib
from pathlib import Path

ENGINE_FILES = [
    "app/engine/graph.py",
    "app/engine/builder.py",
    "app/engine/evaluators.py",
    "app/engine/dfr.py",
    "app/core/canonicalize.py",
]

def compute_engine_version(base_dir: Path) -> str:
    """
    Compute SHA-256 hash of all engine source files to determine version.
    Current Engine Version = Hash(sorted(Hash(file) for file in ENGINE_FILES))
    """
    file_hashes = []
    
    for relative_path in sorted(ENGINE_FILES):
        file_path = base_dir / relative_path
        if not file_path.exists():
            # In dev/early stages, file might not exist yet. 
            # We treat missing file as empty content for stability, or raise error.
            # Raising error is safer for "Strict Governance".
            # For now, we'll log warning and use empty hash to allow bootstrapping.
            print(f"WARNING: Engine file not found: {file_path}")
            content = b""
        else:
            content = file_path.read_bytes()
            
        file_hashes.append(hashlib.sha256(content).hexdigest())
    
    # Hash of the combined hashes
    combined = "".join(file_hashes)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

# Global constant for the runtime version
# We assume this module is imported from backend/app/core/
# So base_dir is ../.. relative to this file?
# Better to use project root env var or relative to file.

CURRENT_FILE = Path(__file__)
PROJECT_ROOT = CURRENT_FILE.parent.parent.parent # backend/app/core/ -> backend/

try:
    ENGINE_VERSION = compute_engine_version(PROJECT_ROOT)
except Exception as e:
    # Fallback for when running in isolation or strange context
    print(f"Error computing engine version: {e}")
    ENGINE_VERSION = "0000000000000000"

def get_cache_key(plan_hash: str) -> str:
    """Construct composite cache key."""
    return f"{plan_hash}:{ENGINE_VERSION}"
