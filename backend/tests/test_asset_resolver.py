import pytest
from pathlib import Path
from app.services.storage.asset_resolver import resolve_image_path, verify_image


def test_resolve_stale_codex_path():
    # Stale container path should resolve to assets/image(1).png
    stale_path = "/workspace/scratch/8be7854de207/upload/image(1).png"
    resolved = resolve_image_path(stale_path)
    assert resolved.exists()
    assert resolved.name == "image(1).png"


def test_verify_image_success():
    stale_path = "/workspace/scratch/8be7854de207/upload/image(1).png"
    resolved = resolve_image_path(stale_path)
    meta = verify_image(resolved)
    assert meta["status"] == "valid"
    assert meta["format"] == "PNG"
    assert meta["width"] == 1024
    assert meta["height"] == 512
    assert meta["file_size_bytes"] > 0


def test_missing_image_raises_clear_error():
    with pytest.raises(FileNotFoundError) as exc_info:
        resolve_image_path("/some/stale/path/completely_missing_photo_99999.png")
    
    assert "genuinely unavailable" in str(exc_info.value)
    assert "Please upload the file again" in str(exc_info.value)


def test_empty_path_raises_value_error():
    with pytest.raises(ValueError):
        resolve_image_path("")
