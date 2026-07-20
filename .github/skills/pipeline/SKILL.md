---
name: pipeline
description: "Development pipeline orchestrator. Use when: starting a new feature, implementing a user story, or any development task that requires the full TDD cycle (plan → test → implement → review → commit). This skill coordinates architect, tester, developer, and reviewer agents in sequence."
---

# Development Pipeline Skill

## Overview
This skill orchestrates the full development lifecycle for the Solver project. It ensures every code change follows:
1. Architecture alignment
2. TDD (Red-Green-Refactor)
3. Code review
4. Git commit with meaningful message

## Pipeline Stages

### Stage 1: PLAN (Architect + PM)
- Invoke `architect` agent to design/update architecture for the feature
- Invoke `pm` agent to clarify requirements and acceptance criteria
- Output: Architecture decision, user stories, acceptance criteria

### Stage 2: RED (Tester)
- Invoke `tester` agent to write failing tests
- Tests MUST cover: happy path, edge cases, error conditions
- Output: Failing test suite

### Stage 3: GREEN (Developer)
- Invoke `developer` agent to implement the feature
- ONLY implement enough to make tests pass
- Output: Passing test suite + implementation

### Stage 4: REFACTOR (Developer + Reviewer)
- Developer refactors for cleanliness
- Invoke `reviewer` agent to review the code
- If reviewer finds issues → back to Stage 3
- Output: Approved code

### Stage 5: COMMIT
- Run full test suite: `python -m pytest tests/ -v`
- Commit with message format: `feat|fix|refactor|test(<scope>): <description>`
- Output: Git commit hash

## Usage
When starting work on a feature, invoke this skill's stages sequentially. Each stage must complete successfully before proceeding to the next.

## Quick Reference
| Stage | Agent | Action | Deliverable |
|-------|-------|--------|-------------|
| PLAN | Architect + PM | Design & scope | Architecture doc, stories |
| RED | Tester | Write tests | Failing tests |
| GREEN | Developer | Implement | Passing tests + code |
| REFACTOR | Developer + Reviewer | Polish & review | Approved code |
| COMMIT | - | Run tests & git | Commit hash |
