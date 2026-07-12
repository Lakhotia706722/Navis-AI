"""Asset selector: maps scene objects to asset library."""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models import Asset

logger = logging.getLogger(__name__)


def find_asset(
    asset_name: str,
    category: Optional[str] = None,
    db: Optional[Session] = None,
) -> Optional[Asset]:
    """
    Find an asset in the library by name and optional category.

    Phase 5+: Real DB queries.
    Phase 3: Falls back to stub if no DB session.

    Args:
        asset_name: Asset to find (e.g., "cargo-vessel-01", "anchor")
        category: Optional category filter
        db: Database session (required for Phase 5+)

    Returns:
        Asset object if found, None otherwise
    """
    # Try exact match in DB if session provided
    if db:
        try:
            asset = db.query(Asset).filter(Asset.name == asset_name).first()
            if asset:
                if category is None or asset.category == category:
                    logger.info(f"Found asset in DB: {asset_name}")
                    return asset
        except Exception as e:
            logger.warning(f"DB asset lookup failed: {e}")

    # Fallback: hardcoded stub library (for Phase 3 testing without DB)
    STUB_ASSETS = {
        "cargo-vessel-01": Asset(
            id=1,
            name="cargo-vessel-01",
            category="vessel",
            tags=["cargo", "ship", "maritime"],
            file_path="s3://maritime-studio/assets/cargo-vessel-01.blend",
            file_format="blend",
            version="1.0",
        ),
        "anchor-01": Asset(
            id=2,
            name="anchor-01",
            category="anchor",
            tags=["anchor", "equipment", "steel"],
            file_path="s3://maritime-studio/assets/anchor-01.blend",
            file_format="blend",
            version="1.0",
        ),
        "rope-coil": Asset(
            id=3,
            name="rope-coil",
            category="rope",
            tags=["rope", "maritime", "equipment"],
            file_path="s3://maritime-studio/assets/rope-coil.blend",
            file_format="blend",
            version="1.0",
        ),
        "deck": Asset(
            id=4,
            name="deck",
            category="vessel",
            tags=["vessel", "deck", "structure"],
            file_path="s3://maritime-studio/assets/deck.blend",
            file_format="blend",
            version="1.0",
        ),
        "sea": Asset(
            id=5,
            name="sea",
            category="environment",
            tags=["sea", "water", "background"],
            file_path="s3://maritime-studio/assets/sea.blend",
            file_format="blend",
            version="1.0",
        ),
        "sky": Asset(
            id=6,
            name="sky",
            category="environment",
            tags=["sky", "background"],
            file_path="s3://maritime-studio/assets/sky.blend",
            file_format="blend",
            version="1.0",
        ),
    }

    if asset_name in STUB_ASSETS:
        asset = STUB_ASSETS[asset_name]
        if category is None or asset.category == category:
            logger.info(f"Found asset in stub library: {asset_name}")
            return asset

    logger.warning(f"Asset not found: {asset_name} (category: {category})")
    return None


def resolve_scene_assets(scene_objects: List[str], db: Optional[Session] = None) -> dict:
    """
    Resolve all objects in a scene to assets.

    Args:
        scene_objects: List of asset names to find
        db: Optional database session

    Returns:
        Dict mapping asset_name → Asset or None
    """
    resolved = {}
    for obj_name in scene_objects:
        asset = find_asset(obj_name, db=db)
        resolved[obj_name] = asset
        if asset:
            logger.info(f"✓ Resolved {obj_name} to {asset.file_path}")
        else:
            logger.warning(f"✗ Could not resolve {obj_name}")

    return resolved
