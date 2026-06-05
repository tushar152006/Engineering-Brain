import logging

from fastapi import APIRouter, BackgroundTasks, Request

from app.agents.code_review_agent import code_review_agent
from app.core.config import settings
from app.models.schemas import GitHubWebhookPRPayload, PRReviewRequest
from app.services.index_store import index_store

logger = logging.getLogger(__name__)

router = APIRouter()

async def process_pr_review(repo_id: str, payload: GitHubWebhookPRPayload):
    try:
        req = PRReviewRequest(
            repo_id=repo_id,
            pr_number=payload.number,
            title=payload.pull_request.get("title", ""),
            body=payload.pull_request.get("body", ""),
            author_login=payload.pull_request.get("user", {}).get("login", ""),
            github_repo=payload.repository.get("full_name"),
            post_to_github=True,
            dry_run=settings.pr_review_dry_run
        )
        await code_review_agent.review_pr(req)
        logger.info(f"Successfully processed PR #{payload.number} for {repo_id}")
    except Exception as e:
        logger.error(f"Failed to process PR review: {e}")

@router.post("/api/github/webhooks")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    # Minimal security validation (could check signature here)
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type == "ping":
        return {"msg": "pong"}
        
    if event_type == "pull_request":
        payload_data = await request.json()
        action = payload_data.get("action")
        
        # Only review on open or synchronize
        if action in ("opened", "synchronize"):
            repo_full_name = payload_data.get("repository", {}).get("full_name")
            
            # Find local repo_id corresponding to this github repo
            repos = await index_store.list_repositories()
            repo_id = None
            for r in repos:
                if r.source == "github" and r.source_url and repo_full_name in r.source_url:
                    repo_id = r.id
                    break
                    
            if not repo_id:
                logger.warning(f"Webhook received for unindexed repo: {repo_full_name}")
                return {"msg": "Repo not indexed"}

            pr_payload = GitHubWebhookPRPayload(
                action=action,
                number=payload_data.get("number"),
                pull_request=payload_data.get("pull_request", {}),
                repository=payload_data.get("repository", {})
            )
            
            # Dispatch to background task
            background_tasks.add_task(process_pr_review, repo_id, pr_payload)
            return {"msg": "PR review triggered"}
            
    return {"msg": f"Ignored event: {event_type}"}
