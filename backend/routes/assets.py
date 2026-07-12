"""Asset library routes (CRUD + search)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.database import get_db
from backend.models import Asset
from backend.routes.auth import get_current_user
from backend.schemas import AssetCreate, AssetResponse, AssetSearchParams
from backend.storage import s3_client

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.post("", response_model=AssetResponse)
async def create_asset(
    asset_create: AssetCreate,
    file: UploadFile = File(...),
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Upload and register a new asset.

    Requires admin or team lead role (MVP: any authenticated user can upload).

    Args:
        asset_create: Asset metadata
        file: Asset file (.blend, .fbx, .glb)
        token: JWT token
        db: Database session

    Returns:
        AssetResponse with registered asset info
    """
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Validate file format
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must have a name",
        )

    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in ["blend", "fbx", "glb"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be .blend, .fbx, or .glb",
        )

    # Check for duplicate asset name
    existing = db.query(Asset).filter(Asset.name == asset_create.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset '{asset_create.name}' already exists",
        )

    # Upload file to S3
    s3_key = f"assets/{asset_create.name}.{file_ext}"
    try:
        # Read file content
        file_content = await file.read()

        # Upload to S3 (using a synchronous call for now)
        # In production, could use async S3 client
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            s3_url = s3_client.upload_file(tmp_path, s3_key)
            if not s3_url:
                raise Exception("S3 upload failed")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )

    # Create asset record in database
    asset = Asset(
        name=asset_create.name,
        category=asset_create.category,
        tags=asset_create.tags,
        file_path=s3_url,
        file_format=file_ext,
        version=asset_create.version,
        licensing_info=asset_create.licensing_info,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    return asset


@router.get("", response_model=List[AssetResponse])
async def list_assets(
    category: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated: "maritime,equipment"
    search: Optional[str] = None,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List/search assets (no auth required for MVP, can restrict later).

    Args:
        category: Filter by category
        tags: Filter by tags (comma-separated)
        search: Search by name/description
        token: JWT token (optional)
        db: Database session

    Returns:
        List of matching assets
    """
    query = db.query(Asset)

    # Category filter
    if category:
        query = query.filter(Asset.category == category)

    # Tag filter (any asset with any of the tags)
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        # Using LIKE for each tag (would be better with ARRAY contains in production)
        tag_conditions = []
        for tag in tag_list:
            tag_conditions.append(Asset.tags.astext.like(f"%{tag}%"))
        if tag_conditions:
            query = query.filter(or_(*tag_conditions))

    # Search filter (name or licensing_info)
    if search:
        query = query.filter(
            or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.licensing_info.ilike(f"%{search}%"),
            )
        )

    assets = query.all()
    return assets


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific asset."""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )
    return asset


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Delete an asset (and S3 file).

    Requires admin role (MVP: any authenticated user).
    """
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Extract S3 key from path
    if asset.file_path.startswith("s3://"):
        # Parse s3://bucket/key
        parts = asset.file_path.split("/", 3)
        if len(parts) == 4:
            s3_key = parts[3]
            s3_client.delete_file(s3_key)

    db.delete(asset)
    db.commit()
    return None
