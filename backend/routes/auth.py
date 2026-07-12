"""Authentication routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from backend.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_create.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Create user
    user = User(
        email=user_create.email,
        hashed_password=hash_password(user_create.password),
        full_name=user_create.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login and get JWT token."""
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(user.id, user.email)
    return {"access_token": access_token}


async def get_current_user(
    authorization: Optional[str] = Header(None), 
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency to get current authenticated user from token."""
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "")

    from backend.security import decode_token

    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == int(token_data.sub)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current user info."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
