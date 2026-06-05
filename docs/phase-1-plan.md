# Phase 1 Implementation Plan

## Objective

Build the first working Engineering Brain loop:

```text
Repo/docs ingestion -> searchable chunks -> cited answers -> architecture summary
```

## Deliverables

- Backend API scaffold.
- Frontend dashboard scaffold.
- In-memory repository index.
- Public GitHub ZIP ingestion.
- Local repository ingestion for development.
- Search endpoint.
- Chat endpoint with citations.
- Architecture summary endpoint.

## Engineering Principles

- Keep interfaces stable even when internals are simple.
- Return citations from the first version.
- Treat repository content as untrusted input.
- Avoid paid services in the MVP path.
- Add managed DB/vector/graph only after the core loop works.

## API Milestone

```text
GET  /health
POST /api/repositories/index
GET  /api/repositories
GET  /api/repositories/{repo_id}
POST /api/search
POST /api/chat
POST /api/architecture-summary
```

## Frontend Milestone

- Repository index form.
- Repository list.
- Stats panel.
- Search box.
- Chat panel.
- Architecture summary panel.

