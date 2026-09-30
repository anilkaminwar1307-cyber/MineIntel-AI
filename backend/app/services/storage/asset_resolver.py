"""
Asset Resolver Utility for MineIntel.

Resolves image and asset paths reliably across varied environments (local, Docker, sandbox),
preventing stale absolute path errors (such as /workspace/scratch/.../upload/...).
Provides file-existence checks, fallback search in project assets/uploads, image verification,
and clear actionable errors without fabricating missing assets.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

# Common root search candidates relative to repository root
WORKSPACE_ROOT = Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) >= 5 else Path.cwd()

DEFAULT_SEARCH_DIRS = [
    Path("assets"),
    Path("frontend/src/assets"),
    Path("frontend/public/assets"),
    Path("data/uploads"),
    Path("backend/data/uploads"),
    Path("sample_data"),
]


def resolve_image_path(input_path: str, search_roots: Optional[list] = None) -> Path:
    """
    Search for and resolve an image path.
    
    1. Tests direct existence of input_path (if valid on current OS).
    2. If not found or path is a stale container/sandbox absolute path, extracts the filename
       and checks candidate directories in the workspace.
    3. Searches recursively in project directories for the filename.
    4. If genuinely unavailable, raises a descriptive FileNotFoundError asking the user
       to upload the image again (never fabricating missing images).
    """
    if not input_path or not str(input_path).strip():
        raise ValueError("Invalid image path provided: path cannot be empty.")

    p = Path(input_path)

    # 1. Direct check
    if p.is_file():
        return p.resolve()

    # 2. Extract basename to search in workspace
    filename = p.name
    candidates = []

    # Build search directories
    search_dirs = list(search_roots) if search_roots else []
    for rel_dir in DEFAULT_SEARCH_DIRS:
        # Check from current working directory and known repository root
        search_dirs.append(Path.cwd() / rel_dir)
        search_dirs.append(WORKSPACE_ROOT / rel_dir)

    # Check immediate candidate folders
    for d in search_dirs:
        candidate = (d / filename).resolve()
        if candidate.is_file():
            return candidate

    # 3. Recursive search in workspace root if not found in immediate candidates
    root_to_search = WORKSPACE_ROOT if WORKSPACE_ROOT.exists() else Path.cwd()
    for found in root_to_search.rglob(filename):
        if found.is_file():
            return found.resolve()

    # 4. Genuinely unavailable: raise clear, explicit fallback error
    raise FileNotFoundError(
        f"Image '{filename}' could not be found in workspace.\n"
        f"Stale path provided: '{input_path}'.\n"
        f"Searched candidate directories: {[str(d) for d in search_dirs if d.exists()]}.\n"
        f"The image is genuinely unavailable. Please upload the file again instead of assuming its presence."
    )


def verify_image(image_path: Path) -> Dict[str, Any]:
    """
    Verifies that the image file exists and can be successfully opened and parsed.
    Returns image metadata (format, dimensions, mode, file_size).
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Cannot verify image: file does not exist at '{image_path}'.")

    try:
        with Image.open(image_path) as img:
            img.verify()
        
        # Re-open to read attributes after verify()
        with Image.open(image_path) as img:
            format_name = img.format
            width, height = img.size
            mode = img.mode

        file_size = image_path.stat().st_size
        return {
            "status": "valid",
            "path": str(image_path.resolve()),
            "format": format_name,
            "width": width,
            "height": height,
            "mode": mode,
            "file_size_bytes": file_size,
        }
    except Exception as e:
        raise ValueError(f"Corrupted or invalid image at '{image_path}': {e}") from e


if __name__ == "__main__":
    import sys
    test_path = sys.argv[1] if len(sys.argv) > 1 else "assets/image(1).png"
    try:
        resolved = resolve_image_path(test_path)
        meta = verify_image(resolved)
        print(f"Successfully resolved and verified image:\n{meta}")
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)
