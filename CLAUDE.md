# CLAUDE.md

This file provides guidance for AI assistants working with the AI-PPT repository.

## Project Overview

AI-PPT is a project for AI-powered presentation generation. The repository is currently in the initial setup phase.

**Repository**: Wangxiaobin123/AI-PPT
**Primary branch**: `master`
**Development branch**: `dev`

## Repository Structure

```
AI-PPT/
├── README.md          # Project readme
└── CLAUDE.md          # This file — AI assistant guidance
```

The project is newly initialized. As source code is added, this section should be updated to reflect the directory layout and architecture.

## Development Setup

No build tools, package managers, or dependencies are configured yet. When they are added, document the setup steps here:

1. Clone the repository
2. (To be defined) Install dependencies
3. (To be defined) Run development server
4. (To be defined) Run tests

## Build & Test Commands

No build or test commands are configured yet. Update this section as tooling is added.

<!--
Example (update when applicable):
- `npm install` — install dependencies
- `npm run dev` — start development server
- `npm run build` — production build
- `npm test` — run all tests
- `npm run lint` — run linter
-->

## Code Conventions

No linting, formatting, or type-checking tools are configured yet. When added, document them here.

## Git Workflow

- `master` — stable branch
- `dev` — active development branch
- Feature branches should be created off `dev` and merged back via pull request

## Key Guidelines for AI Assistants

1. **Read before editing** — Always read files before proposing changes.
2. **Minimal changes** — Only make changes that are directly requested or clearly necessary. Avoid over-engineering.
3. **No secrets in commits** — Never commit `.env` files, API keys, credentials, or other sensitive data.
4. **Update this file** — When adding significant new tooling, directories, or conventions, update this CLAUDE.md to keep it current.
5. **Test your changes** — Once a test framework is set up, run tests before committing.
