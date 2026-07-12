"""Tests for security utilities."""
import pytest
from backend.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)


class TestPasswordHashing:
    """Password hashing tests."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "my_secret_password"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "my_secret_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "my_secret_password"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) is False

    def test_hash_consistency(self):
        """Test that hashing same password gives different hashes (bcrypt salt)."""
        password = "password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTToken:
    """JWT token tests."""

    def test_create_access_token(self):
        """Test token creation."""
        user_id = 123
        email = "test@example.com"
        token = create_access_token(user_id, email)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_token_valid(self):
        """Test decoding a valid token."""
        user_id = 123
        email = "test@example.com"
        token = create_access_token(user_id, email)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded.sub == str(user_id)
        assert decoded.email == email

    def test_decode_token_invalid(self):
        """Test decoding an invalid token."""
        token = "invalid.token.here"
        decoded = decode_token(token)
        assert decoded is None

    def test_decode_token_expired(self):
        """Test that expired token is rejected."""
        # This would require mocking time, so we'll do a simpler version
        from datetime import datetime, timedelta
        from jose import jwt
        from backend.config import settings

        # Create a token that's already expired
        to_encode = {
            "sub": "123",
            "email": "test@example.com",
            "exp": datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        }
        expired_token = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        decoded = decode_token(expired_token)
        assert decoded is None
