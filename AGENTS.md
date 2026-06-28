# CLAUDE.md

This file provides guidance when working with code in this repository.

## Project Overview

Laoshi Coach is a language learning application (currently supporting Mandarin Chinese and Japanese) that helps users practice sentence formation using vocabulary words. Users organize vocabulary into decks with per-deck language tagging, practice creating sentences with target words, and receive AI-powered evaluation and feedback. The app uses spaced repetition (SM-2 algorithm) to optimize review scheduling based on user self-ratings of word mastery.

## Repository Overview

This is a monorepo containing a React frontend and Python Flask backend code. See each sub-directory's CLAUDE.md for specific guidelines.

## Architecture
- Check @.claude/architecture.md for tech stack, repository structure, data models and full list of API endpoints


## Development Workflow
- Always start with the why of the development work  (refer to PRD.md)
- Check PHASE_1_PROJECT_PLAN.md for Phase 1 (webapp) development state
- Then write the detailed documentation (requirements.md, design.md, and tasks.md) for the feature, and seek human approval on it
- Refer closely to this documentation when developing
- Spin up sub-agents to speed up development work, but ensure all agents follow the documentation as the source-of-truth
- Write your own tests and ensure that all tests pass before asking the human to review
