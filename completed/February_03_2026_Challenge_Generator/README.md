# Challenge #1: Daily AI Challenge Generator

**Date:** February 03, 2026
**Domain:** AI Agent Creation / Automation
**Tool Focus:** Claude Code + Anthropic API
**Time:** ~2 hours
**Status:** Completed ✅

## Challenge Summary

Built an automated daily challenge generator that creates personalized AI skills training tasks, tracks progress, and maintains a portfolio log.

## What I Built

A Python-based AI agent that:
1. **Calls the Anthropic API** to generate unique daily challenges
2. **Checks previous challenges** to avoid duplicates (same domain + skills)
3. **Generates sample data files** (CSV, JSON) for hands-on practice
4. **Maintains a portfolio log** with structured summaries
5. **Auto-pushes to GitHub** via GitHub Actions (runs daily at 4:30 PM London time)

## Technical Highlights

- **LangChain Tools integration** for structured API calls
- **Prompt engineering** for consistent, high-quality challenge generation
- **Regex parsing** for extracting structured data from AI responses
- **GitHub Actions workflow** for cloud automation
- **Environment variable management** for secure API key handling

## Files

| File | Purpose |
|------|---------|
| `Main.py` | Core generator script (local version) |
| `Plan.md` | Original planning document |
| `.gitignore` | Protects sensitive files |

## Skills Trained

- API integration (Anthropic)
- Python scripting & automation
- Prompt engineering
- Git/GitHub workflows
- GitHub Actions (CI/CD)
- Environment management
- Code organization

## Key Learnings

1. GitHub Actions can run scheduled tasks without keeping my PC on
2. Using AI to extract structured data from AI-generated text works well
3. Portfolio tracking from day one creates accountability

## Setup (if replicating)

```bash
pip install anthropic langchain python-dotenv
```

Create `.env`:
```
ANTHROPIC_API_KEY=your-key-here
```

Run:
```bash
python Main.py
```
