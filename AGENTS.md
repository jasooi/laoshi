# CLAUDE.md

This file provides guidance when working with code in this repository.

## Project Overview

Laoshi Coach is a Mandarin Chinese language learning application that helps users practice sentence formation using vocabulary words. Users import vocabulary, practice creating sentences with target words, and receive AI-powered evaluation and feedback with confidence score tracking.

## Repository Overview

This is a monorepo containing a React frontend and Python Flask backend code. See each sub-directory's CLAUDE.md for specific guidelines.

## Architecture
- Check @.claude/architecture.md for tech stack, repository structure, data models and full list of API endpoints


## Development Workflow
- Always start with the why of the development work  (refer to PRD.md)
- Check PROJECT_PLAN.md for the current state of development
- Then write the detailed documentation (requirements.md, design.md, and tasks.md) for the feature, and seek human approval on it
- Refer closely to this documentation when developing
- Spin up sub-agents to speed up development work, but ensure all agents follow the documentation as the source-of-truth
- Write your own tests and ensure that all tests pass before asking the human to review
