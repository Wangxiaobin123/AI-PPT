# AI-PPT

Skill-Driven Intelligent Content Production System — generate PPTX, DOCX, XLSX, PDF, and HTML documents from natural language instructions.

## Features

- **Intent Understanding** — LLM-powered natural language parsing with keyword fallback
- **5 Document Generators** — PowerPoint, Word, Excel, PDF, HTML
- **6 Input Parsers** — Markdown, HTML, CSV, JSON, plain text, Office files
- **Pluggable Skills** — Public + user-defined custom skills with auto-discovery
- **Execution Pipeline** — Task decomposition, parallel execution, QA validation
- **REST API** — FastAPI-based web service with OpenAPI docs
- **Claude Code Integration** — Auto-imported skills for seamless AI-assisted generation

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys (optional — system works without LLM keys)

# Start the server
make dev
# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

## Usage

### Via API

```bash
# Generate a PowerPoint presentation
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "format": "pptx",
    "content": "# AI Trends\n\n## Machine Learning\n- Deep learning\n- NLP\n- Computer vision",
    "content_format": "markdown"
  }'

# Natural language intent
curl -X POST http://localhost:8000/api/v1/intent \
  -H "Content-Type: application/json" \
  -d '{"text": "Create a presentation about AI trends"}'
```

### Via Docker

```bash
docker compose up
```

## Architecture

```
User Input → Intent Engine → Skills Registry → Execution Engine → Output
              (LLM/keyword)   (match skill)    (generate + QA)    (file)
```

Four core modules:
1. **Intent Engine** — Classifies intent, extracts parameters, decomposes tasks
2. **Skills Registry** — Discovers and manages document generation skills
3. **Execution Engine** — Runs tasks with QA validation
4. **Output & Delivery** — File storage and download API

## Development

```bash
make test       # Run 29 tests
make lint       # Lint with ruff
make format     # Format with ruff
make typecheck  # Type check with mypy
```

## License

MIT
