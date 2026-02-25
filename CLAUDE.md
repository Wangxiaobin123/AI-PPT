# CLAUDE.md

This file provides guidance for AI assistants working with the AI-PPT repository.

## Project Overview

AI-PPT is a **Skill-Driven Intelligent Content Production System** that generates documents (PPTX, DOCX, XLSX, PDF, HTML) from natural language instructions. It features an LLM-based intent engine, a pluggable skills registry, an execution pipeline with QA validation, and a FastAPI web API.

**Repository**: Wangxiaobin123/AI-PPT
**Primary branch**: `master`
**Development branch**: `dev`
**Language**: Python 3.10+
**Framework**: FastAPI

## Repository Structure

```
AI-PPT/
├── .claude/skills/           # Claude Code Skills (auto-imported)
│   ├── pptx/                 # PowerPoint generation skill
│   ├── docx/                 # Word document skill
│   ├── xlsx/                 # Excel spreadsheet skill
│   ├── pdf/                  # PDF generation skill
│   ├── html-design/          # HTML/web page skill
│   └── content-producer/     # Meta-skill (orchestrator)
│
├── src/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Pydantic Settings (from .env)
│   ├── dependencies.py       # FastAPI dependency injection
│   │
│   ├── core/                 # Module A: Intent Engine
│   │   ├── intent/           # Classifier, parameter extractor, conversation
│   │   ├── task/             # Task models, decomposer, scheduler
│   │   └── llm/              # LLM client (Anthropic + OpenAI providers)
│   │
│   ├── skills/               # Module B: Skills Registry
│   │   ├── base.py           # BaseSkill ABC
│   │   ├── registry.py       # SkillRegistry (discover/register/match)
│   │   ├── loader.py         # Dynamic skill loading
│   │   ├── public/           # Built-in skills (pptx, docx, xlsx, pdf, html)
│   │   └── user/             # User-defined custom skills
│   │
│   ├── engine/               # Module C: Execution Engine
│   │   ├── executor.py       # TaskExecutor
│   │   ├── renderer.py       # FileRenderer
│   │   ├── qa.py             # QAValidator
│   │   └── pipeline.py       # ExecutionPipeline
│   │
│   ├── output/               # Module D: Output & Delivery
│   ├── api/v1/               # REST API (endpoints, schemas, middleware)
│   ├── parsers/              # Input parsers (markdown, html, csv, json, text, office)
│   ├── generators/           # Document generators (pptx, docx, xlsx, pdf, html)
│   └── utils/                # Logging, exceptions, file utilities
│
├── tests/
│   ├── unit/                 # Unit tests for each module
│   └── integration/          # API integration tests
│
├── pyproject.toml            # Project metadata & dependencies
├── requirements.txt          # Pinned dependencies
├── Makefile                  # Dev commands
├── Dockerfile                # Container image
└── docker-compose.yml        # Docker composition
```

## Development Setup

1. Clone the repository
2. `pip install -r requirements.txt` — install dependencies
3. `cp .env.example .env` — configure environment variables
4. `make dev` — start development server (http://localhost:8000)
5. `make test` — run test suite

## Build & Test Commands

- `make install` — install production dependencies
- `make install-dev` — install dev dependencies (pytest, ruff, mypy)
- `make dev` — start FastAPI dev server with hot reload
- `make test` — run all tests (`pytest tests/ -v`)
- `make lint` — lint with ruff
- `make format` — format with ruff
- `make typecheck` — type check with mypy

## Code Conventions

- **Formatter/Linter**: ruff (line-length=100, target Python 3.10)
- **Type checking**: mypy
- **Testing**: pytest + pytest-asyncio
- **Data models**: Pydantic v2 BaseModel throughout
- **Async**: All generators, skills, and API endpoints are async
- **Naming**: Classes use PascalCase, files use snake_case, skills use lowercase names

## Architecture

### Four Core Modules

1. **Intent Engine** (`src/core/`) — Parses natural language → classifies intent → extracts parameters → decomposes into tasks → schedules execution. Falls back to keyword matching when no LLM API key is configured.

2. **Skills Registry** (`src/skills/`) — Auto-discovers skill modules from `public/` and `user/` directories. Each skill implements `BaseSkill` with `metadata`, `validate_params()`, `execute()`, and `qa_check()`.

3. **Execution Engine** (`src/engine/`) — Runs task plans: validates params → executes skill → renders file → QA validation. Supports parallel execution of independent tasks.

4. **Output & Delivery** (`src/output/`, `src/api/`) — File storage, download URLs, REST API endpoints.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/intent` | Submit natural language intent |
| POST | `/api/v1/generate` | Direct document generation |
| GET | `/api/v1/skills` | List available skills |
| GET | `/api/v1/files/{id}` | Download generated file |

## Git Workflow

- `master` — stable branch
- `dev` — active development branch
- Feature branches should be created off `dev` and merged back via pull request

## Key Guidelines for AI Assistants

1. **Read before editing** — Always read files before proposing changes.
2. **Minimal changes** — Only make changes that are directly requested or clearly necessary.
3. **No secrets in commits** — Never commit `.env` files, API keys, or credentials.
4. **Run tests** — `make test` before committing. All 29 tests must pass.
5. **Update this file** — When adding new modules or changing architecture, update this CLAUDE.md.
6. **Use the skills** — Claude Code skills are in `.claude/skills/`. Use `/pptx`, `/docx`, etc. for document generation.
