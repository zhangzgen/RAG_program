# -*- coding: utf-8 -*-
import os
import sys
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

try:
    import jwt
except ImportError:
    import PyJWT as jwt

from base import Config, logger


class AuthService:
    """JWT auth service."""

    def __init__(self):
        self.logger = logger
        self.reload_config()

    def reload_config(self):
        self.config = Config()
        self.secret_key = self.config.JWT_SECRET_KEY
        self.algorithm = self.config.JWT_ALGORITHM
        self.expire_days = self.config.JWT_EXPIRE_DAYS

    def generate_token(self, user_id, email):
        """Generate a JWT token."""
        try:
            self.reload_config()
            expire_time = datetime.utcnow() + timedelta(days=self.expire_days)
            payload = {
                "user_id": user_id,
                "email": email,
                "exp": expire_time,
                "iat": datetime.utcnow(),
            }
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            self.logger.info(f"JWT token generated: user_id={user_id}, email={email}")
            return token
        except Exception as exc:
            self.logger.error(f"Failed to generate JWT token: {exc}")
            raise

    def verify_token(self, token):
        """Verify and decode a JWT token."""
        try:
            self.reload_config()
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            self.logger.info(f"JWT token verified: user_id={payload.get('user_id')}")
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as exc:
            self.logger.error(f"JWT token invalid: {exc}")
            return None
        except Exception as exc:
            self.logger.error(f"JWT token verification failed: {exc}")
            return None

    def decode_token_without_verification(self, token):
        """Decode a token payload without signature verification (debug only)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as exc:
            self.logger.error(f"Failed to decode JWT token: {exc}")
            return None


if __name__ == "__main__":
    auth_service = AuthService()
    token = auth_service.generate_token(user_id=1, email="test@example.com")
    print(f"token: {token}")
    payload = auth_service.verify_token(token)
    print(f"payload: {payload}")
