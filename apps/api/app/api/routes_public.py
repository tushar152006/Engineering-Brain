import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.models.schemas import (
    ArchitectureSummaryRequest,
    IndexRepositoryRequest,
    PublicAnalyzeRequest,
    PublicReportResponse,
    PublicReportStatus,
    RepositorySource,
)
from app.services.architecture_service import architecture_service
from app.services.index_store import index_store

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for public reports (MVP)
_public_reports: dict[str, PublicReportResponse] = {}

async def generate_public_report(report_id: str, repo_id: str, github_url: str):
    """Background task to index repo and generate architecture report."""
    try:
        # 1. Index the repo
        req = IndexRepositoryRequest(
            source=RepositorySource.github,
            url=github_url
        )
        
        from app.services.repository_loader import normalize_github_url
        from app.services.repository_service import _run_indexing
        name = normalize_github_url(github_url)[0]

        await _run_indexing(
            repo_id=repo_id,
            name=name,
            source=RepositorySource.github,
            source_url=github_url,
            payload=req
        )
        
        # 2. Generate architecture summary
        arch_req = ArchitectureSummaryRequest(repo_id=repo_id)
        # Attempt to get LLM narrative
        arch_resp = await architecture_service.summarize_deep(arch_req)
        
        # 3. Update report
        report = _public_reports[report_id]
        report.status = PublicReportStatus.ready
        report.repo_name = arch_resp.repository.name
        report.summary = arch_resp.llm_narrative or arch_resp.summary
        report.languages = arch_resp.repository.languages
        report.frameworks = [f.model_dump() for f in arch_resp.frameworks]
        report.top_directories = [d.model_dump() for d in arch_resp.top_directories]
        report.entrypoints = arch_resp.entrypoints
        report.important_files = arch_resp.important_files
        report.symbol_count = arch_resp.symbol_count
        report.file_count = arch_resp.repository.file_count
        report.next_steps = arch_resp.next_steps
        
    except Exception as e:
        logger.error(f"Failed to generate public report {report_id}: {e}")
        if report_id in _public_reports:
            _public_reports[report_id].status = PublicReportStatus.failed
            _public_reports[report_id].error = str(e)


@router.post("/api/public/analyze", response_model=PublicReportResponse)
async def analyze_public_repo(request: Request, payload: PublicAnalyzeRequest, background_tasks: BackgroundTasks):
    """Start analysis of a public repo and return a report ID."""
    report_id = str(uuid.uuid4())
    repo_id = str(uuid.uuid4())
    
    report = PublicReportResponse(
        report_id=report_id,
        github_url=payload.github_url,
        status=PublicReportStatus.analyzing,
        created_at=datetime.now(UTC).isoformat()
    )
    _public_reports[report_id] = report
    
    # Initialize repository placeholder so worker can update it
    index_store.create_repository(repo_id, payload.github_url, RepositorySource.github, payload.github_url)
    
    background_tasks.add_task(generate_public_report, report_id, repo_id, payload.github_url)
    
    return report

@router.get("/api/public/reports/{report_id}", response_model=PublicReportResponse)
def get_public_report(report_id: str):
    """Get the status/content of a public repo report."""
    if report_id not in _public_reports:
        raise HTTPException(status_code=404, detail="Report not found")
    return _public_reports[report_id]
