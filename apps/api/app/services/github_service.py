import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class GitHubService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)

    async def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str | None:
        """Fetch the unified diff of a GitHub pull request."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            resp = await self.client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"Failed to fetch PR diff for {owner}/{repo}#{pr_number}: {e}")
            return None

    async def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str) -> bool:
        """Post a comment to a GitHub pull request."""
        if settings.pr_review_dry_run:
            logger.info(f"[DRY RUN] Would post comment to {owner}/{repo}#{pr_number}:\n{body}")
            return True

        if not settings.github_token:
            logger.error("Cannot post PR comment: GITHUB_TOKEN is not set.")
            return False

        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {settings.github_token}",
        }
        
        try:
            resp = await self.client.post(url, headers=headers, json={"body": body})
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to post PR comment to {owner}/{repo}#{pr_number}: {e}")
            return False

github_service = GitHubService()
