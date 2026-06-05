import json
import logging
import uuid

from app.core.config import settings
from app.llm.ollama_adapter import ollama_adapter
from app.models.schemas import (
    PRReviewRequest,
    PRReviewResponse,
    ReviewComment,
    AgentRun,
    AgentRunStatus,
)
from datetime import datetime, UTC
from app.retrieval.ranking import hybrid_rank_chunks
from app.services.github_service import github_service
from app.services.index_store import index_store

logger = logging.getLogger(__name__)

_PR_REVIEW_PROMPT = """\
You are a senior staff engineer reviewing a Pull Request.
Given the PR Diff and the codebase evidence (architecture, docs, related code), provide a review.

Output MUST be a valid JSON object with the following schema:
{
    "summary": "1-2 sentence overall summary of the PR",
    "risk_summary": "high" | "medium" | "low" | "clean",
    "missing_tests": ["List of suggested tests or empty"],
    "comments": [
        {
            "file_path": "path to file",
            "line": 123,
            "risk": "high",
            "category": "architecture",
            "message": "The issue",
            "suggestion": "How to fix it",
            "confidence": "high",
            "evidence": ["list of cited files"]
        }
    ]
}

Focus on architecture violations, logic errors, and missing tests. Do not nitpick style.
If there are no issues, return empty list for comments and "clean" for risk_summary.
"""

class CodeReviewAgent:
    async def review_pr(self, payload: PRReviewRequest, run_id: str | None = None) -> PRReviewResponse:
        run_id = run_id or str(uuid.uuid4())
        started_at = datetime.now(UTC).isoformat()

        run_record = AgentRun(
            id=run_id,
            repo_id=payload.repo_id,
            agent_type="pr_review",
            status=AgentRunStatus.running,
            input=payload.model_dump(),
            started_at=started_at,
        )
        index_store.save_agent_run(run_record)

        try:
            diff = payload.diff
            if not diff and payload.github_repo and payload.pr_number:
                owner, repo_name = payload.github_repo.split("/")
                diff = await github_service.get_pr_diff(owner, repo_name, payload.pr_number)
                
            if not diff:
                raise ValueError("No diff provided and failed to fetch from GitHub.")

            # Simple changed files parsing from diff
            changed_files = []
            for line in diff.splitlines():
                if line.startswith("+++ b/"):
                    changed_files.append(line[6:])

            # Get relevant codebase chunks (simple heuristic: embed the diff or use changed files as query)
            query = f"PR Title: {payload.title}\nFiles: {' '.join(changed_files)}"
            query_embedding = await ollama_adapter.embed(query)
            chunks = index_store.get_chunks(payload.repo_id)
            
            citations = hybrid_rank_chunks(query, query_embedding, chunks, limit=10)
            
            evidence = "\n".join([f"File: {c.file_path}\n{c.excerpt}" for c in citations])
            
            prompt = f"PR Diff:\n{diff[:4000]}\n\nCodebase Evidence:\n{evidence}"
            
            llm_response = await ollama_adapter.generate(
                prompt,
                system=_PR_REVIEW_PROMPT,
                temperature=0.1
            )

            # Parse JSON
            try:
                clean_json = llm_response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:-3].strip()
                elif clean_json.startswith("```"):
                    clean_json = clean_json[3:-3].strip()
                    
                parsed = json.loads(clean_json)
            except Exception as e:
                logger.error(f"Failed to parse LLM JSON output: {e}\nRaw output: {llm_response}")
                parsed = {
                    "summary": "Failed to parse LLM output.",
                    "risk_summary": "low",
                    "missing_tests": [],
                    "comments": []
                }

            # Format comments
            comments = []
            for c in parsed.get("comments", []):
                try:
                    comments.append(ReviewComment(**c))
                except Exception as e:
                    logger.warning(f"Skipping malformed comment: {e}")

            # Post to GitHub if requested
            posted = False
            if payload.post_to_github and not payload.dry_run and payload.github_repo and payload.pr_number:
                owner, repo_name = payload.github_repo.split("/")
                comment_body = f"## Code Review Summary\n**Risk**: {parsed.get('risk_summary')}\n\n{parsed.get('summary')}\n\n"
                for c in comments:
                    comment_body += f"- **{c.file_path}**: {c.message} (Suggestion: {c.suggestion})\n"
                posted = await github_service.post_pr_comment(owner, repo_name, payload.pr_number, comment_body)

            model_name = f"ollama/{settings.ollama_chat_model}" if llm_response else None

            response = PRReviewResponse(
                run_id=run_id,
                repo_id=payload.repo_id,
                pr_number=payload.pr_number,
                comments=comments,
                risk_summary=parsed.get("risk_summary", "low"),
                summary=parsed.get("summary", "No summary provided."),
                missing_tests=parsed.get("missing_tests", []),
                changed_files=changed_files,
                model_used=model_name,
                posted_to_github=posted,
                dry_run=payload.dry_run
            )

            # Update run record to done
            run_record.status = AgentRunStatus.done
            run_record.output = response.model_dump()
            run_record.model = model_name
            run_record.completed_at = datetime.now(UTC).isoformat()
            index_store.save_agent_run(run_record)

            return response

        except Exception as e:
            logger.error(f"Code review agent run {run_id} failed: {e}")
            run_record.status = AgentRunStatus.failed
            run_record.error = str(e)
            run_record.completed_at = datetime.now(UTC).isoformat()
            index_store.save_agent_run(run_record)
            raise

code_review_agent = CodeReviewAgent()
