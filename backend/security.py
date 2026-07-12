"""JWT and password security utilities."""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    """JWT token claims."""

    sub: str  # user_id as string
    email: str
    exp: datetime


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, email: str) -> str:
    """Create a JWT access token."""
    to_encode = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.utcnow() + settings.jwt_expiration,
    }
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        email: str = payload.get("email")
        if user_id is None or email is None:
            return None
        return TokenData(
            sub=user_id,
            email=email,
            exp=datetime.fromtimestamp(payload.get("exp")),
        )
    except JWTError:
        return None
