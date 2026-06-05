"""GitHub OAuth integration for user authentication and GitHub App webhooks."""

from __future__ import annotations

import hmac
import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

import httpx
import jwt
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitHubUser(BaseModel):
    """GitHub user from OAuth token."""
    id: int
    login: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    name: Optional[str] = None


class GitHubOAuthHandler:
    """Handles GitHub OAuth 2.0 flow."""

    def __init__(self):
        self._client_id = settings.github_client_id
        self._client_secret = settings.github_client_secret
        self._redirect_uri = settings.github_oauth_redirect_uri

    def get_authorization_url(self, state: str) -> str:
        """Get GitHub OAuth authorization URL."""
        return (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={self._client_id}"
            f"&redirect_uri={self._redirect_uri}"
            f"&scope=repo,user"
            f"&state={state}"
        )

    async def exchange_code_for_token(self, code: str) -> str | None:
        """Exchange authorization code for access token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://github.com/login/oauth/access_token",
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "code": code,
                        "redirect_uri": self._redirect_uri,
                    },
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("access_token")
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            return None

    async def get_user(self, token: str) -> GitHubUser | None:
        """Get GitHub user info from token."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                data = response.json()
                return GitHubUser(
                    id=data["id"],
                    login=data["login"],
                    email=data.get("email"),
                    avatar_url=data.get("avatar_url"),
                    name=data.get("name"),
                )
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None


class GitHubAppHandler:
    """Handles GitHub App authentication and webhooks."""

    def __init__(self):
        self._app_id = settings.github_app_id
        self._private_key = settings.github_app_private_key
        self._webhook_secret = settings.github_webhook_secret

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from GitHub."""
        if not self._webhook_secret:
            logger.warning("GitHub webhook secret not configured")
            return False

        expected_signature = "sha256=" + hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    def get_app_jwt(self) -> str:
        """Generate JWT for GitHub App authentication."""
        if not self._private_key:
            raise ValueError("GitHub App private key not configured")

        now = datetime.now(UTC)
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iss": self._app_id,
        }

        return jwt.encode(
            payload,
            self._private_key,
            algorithm="RS256",
        )

    async def get_installation_token(self, installation_id: int) -> str | None:
        """Get installation access token from GitHub App."""
        try:
            jwt_token = self.get_app_jwt()
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                    headers={
                        "Authorization": f"Bearer {jwt_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("token")
        except Exception as e:
            logger.error(f"Failed to get installation token: {e}")
            return None

    async def get_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        installation_id: int,
    ) -> str | None:
        """Get PR diff from GitHub."""
        try:
            token = await self.get_installation_token(installation_id)
            if not token:
                return None

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}.diff",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.error(f"Failed to get PR diff: {e}")
            return None

    async def post_pr_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        installation_id: int,
    ) -> bool:
        """Post review comment on PR."""
        try:
            token = await self.get_installation_token(installation_id)
            if not token:
                return False

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
                    json={"body": body},
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to post PR comment: {e}")
            return False


# Global instances
_oauth_handler: GitHubOAuthHandler | None = None
_app_handler: GitHubAppHandler | None = None


def get_oauth_handler() -> GitHubOAuthHandler:
    """Get GitHub OAuth handler."""
    global _oauth_handler
    if _oauth_handler is None:
        _oauth_handler = GitHubOAuthHandler()
    return _oauth_handler


def get_app_handler() -> GitHubAppHandler:
    """Get GitHub App handler."""
    global _app_handler
    if _app_handler is None:
        _app_handler = GitHubAppHandler()
    return _app_handler
