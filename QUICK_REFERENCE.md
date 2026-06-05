# Engineering Brain - Quick Reference Guide

## Quick Start (5 minutes)

### 1. Start Backend
```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
Access: `http://localhost:8000/docs` (API docs)

### 2. Start Frontend  
```bash
cd apps/web
npm install
npm run dev
```
Access: `http://localhost:5173`

### 3. Index a Repository
1. Open `http://localhost:5173`
2. Click "Index Repository"
3. Enter: `https://github.com/torvalds/linux` (public) or local path
4. Wait for indexing to complete (visible in Status tab)
5. Try searching!

---

## Common Tasks

### Search for Code
```bash
POST http://localhost:8000/api/search
{
  "repo_id": "abc123",
  "query": "authentication",
  "limit": 8
}
```

### Ask a Question
```bash
POST http://localhost:8000/api/chat
{
  "repo_id": "abc123",
  "question": "How does the auth system work?",
  "limit": 6
}
```

### Get Architecture Summary
```bash
POST http://localhost:8000/api/architecture-summary
{
  "repo_id": "abc123"
}
```

### Review a PR
```bash
POST http://localhost:8000/api/agents/pr-review
{
  "repo_id": "abc123",
  "pr_number": 42,
  "title": "Add authentication",
  "diff": "...",
  "dry_run": true
}
```

---

## Key Files Reference

| File | Purpose | LOC |
|---|---|---|
| `app/main.py` | FastAPI app setup | 30 |
| `app/api/routes.py` | All HTTP endpoints | 400 |
| `app/services/repository_service.py` | Indexing orchestration | 200 |
| `app/retrieval/chunker.py` | Code/doc chunking | 250 |
| `app/retrieval/ranking.py` | Hybrid search | 200 |
| `app/llm/ollama_adapter.py` | LLM interface | 200 |
| `app/services/cache_service.py` | Performance caching | 250 |
| `app/agents/code_review_agent.py` | PR review | 160 |

---

## Important Directories

```
.engineering-brain/
└─ index-store.json        # Persisted data (in-memory mode)

apps/api/
├─ app/services/           # Business logic
├─ app/retrieval/          # Search & ranking
├─ app/agents/             # AI agents
├─ app/llm/                # LLM adapters
└─ tests/                  # Test suite

apps/web/src/
├─ App.tsx                 # Main UI component
├─ api.ts                  # API client
└─ types.ts                # TypeScript definitions
```

---

## Environment Setup

### Required
```bash
OLLAMA_BASE_URL=http://127.0.0.1:11434
ENABLE_LLM=true
ENABLE_EMBEDDINGS=true
```

### Optional
```bash
GITHUB_TOKEN=ghp_...
GITHUB_APP_ID=12345
PR_REVIEW_DRY_RUN=true
```

---

## Testing

```bash
# Run all tests
cd apps/api
pytest tests/ -v

# Run specific test
pytest tests/test_comprehensive.py::TestChunking::test_markdown_chunks_by_heading -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Debugging

### See API Logs
```bash
# Already visible in terminal running uvicorn
# Look for [INFO], [WARNING], [ERROR] prefixes
```

### Check Index Store
```bash
cat .engineering-brain/index-store.json | python -m json.tool | head -100
```

### Test Ollama Connection
```bash
curl http://127.0.0.1:11434/api/tags
# Returns available models
```

### Clear Index
```bash
rm -rf .engineering-brain/
# Restart backend to create fresh
```

---

## Performance Tips

1. **Faster Search**: Use caching
   - First search: 150-200ms (embedding + ranking)
   - Cached: 10-50ms
   - Cache TTL: 10 minutes

2. **Faster Indexing**: Use smaller repos first
   - <100 files: <1s
   - <1000 files: 5-10s
   - >5000 files: 30-60s

3. **Faster Chat**: Use embeddings
   - Without embeddings: keyword-only (~100ms)
   - With embeddings: semantic (~1-2s for LLM)

4. **Monitor Memory**: In-memory store
   - ~500 repos max before slowdown
   - Each repo ~10-20MB indexed
   - Use Phase 4 database for scale

---

## Monitoring

### Check System Health
```bash
curl http://localhost:8000/health
# Returns: {"status": "ok"}
```

### Get LLM Status
```bash
GET http://localhost:8000/api/llm/status
# Returns availability of Ollama
```

### View Cache Stats
```python
from app.services.cache_service import cache_service
stats = cache_service.stats()
print(stats)
```

---

## Common Issues

### "Ollama not reachable"
- Start Ollama: `ollama serve`
- Check: `curl http://127.0.0.1:11434/api/tags`
- Backend will work without it (citations-only mode)

### "Repository not found"
- Ensure indexing is complete (status = "ready")
- Check in status tab of UI

### "Search returns no results"
- Check that chunks were created (status shows chunk_count > 0)
- Try simpler query keywords
- Enable embeddings in config

### "PR Review fails"
- Ensure repo is indexed first
- Check diff format is correct
- Use dry_run=true to test

---

## Deployment Checklist

Before production:
- [ ] Database migration (Phase 4)
- [ ] Error monitoring (Sentry)
- [ ] Performance monitoring (Prometheus)
- [ ] GitHub App OAuth setup
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Backup strategy in place
- [ ] Load testing passed

---

## Resources

- **API Docs**: `http://localhost:8000/docs`
- **Implementation Report**: [`IMPLEMENTATION_REPORT.md`](./IMPLEMENTATION_REPORT.md)
- **Blueprint**: [`docs/Engineering-Brain-Startup-Blueprint.md`](./docs/Engineering-Brain-Startup-Blueprint.md)
- **Session Summary**: [`SESSION_SUMMARY.md`](./SESSION_SUMMARY.md)

---

## Getting Help

1. Check logs in terminal
2. Review API docs at `/docs`
3. Read `IMPLEMENTATION_REPORT.md` for architecture
4. Run tests to verify setup
5. Check GitHub issues/discussions

---

**Last Updated**: June 5, 2026  
**Version**: 1.0.0 (Production Ready)
