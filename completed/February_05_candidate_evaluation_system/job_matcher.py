"""
Job Matcher Module
==================
Uses Claude API to evaluate each resume against job descriptions using the scoring rubric.
"""

import csv
import json
import re
import time

import anthropic

from config import (
    JOB_DESCRIPTIONS_PATH,
    SCORING_RUBRIC_PATH,
    SALARY_BENCHMARKS_PATH,
    MODEL_NAME,
    MAX_TOKENS,
    API_DELAY_SECONDS,
    MAX_RETRIES,
)


def load_job_descriptions() -> list[dict]:
    """Load job descriptions from JSON file."""
    with open(JOB_DESCRIPTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scoring_rubric() -> list[dict]:
    """Load scoring rubric from CSV into structured list."""
    rubric = []
    with open(SCORING_RUBRIC_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rubric.append(
                {
                    "criteria": row["Criteria"],
                    "weight": float(row["Weight"]),
                    "descriptors": {
                        1: row["Score_1_Poor"],
                        2: row["Score_2_Fair"],
                        3: row["Score_3_Good"],
                        4: row["Score_4_Very_Good"],
                        5: row["Score_5_Excellent"],
                    },
                }
            )
    return rubric


def load_salary_benchmarks() -> dict:
    """Load salary benchmarks into a lookup dict keyed by (Position, Level)."""
    benchmarks = {}
    with open(SALARY_BENCHMARKS_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["Position"].strip(), row["Level"].strip())
            benchmarks[key] = {
                "min": int(row["Min_Salary"]),
                "max": int(row["Max_Salary"]),
                "median": int(row["Median_Salary"]),
                "trend": row["Market_Trend"].strip(),
            }
    return benchmarks


def build_scoring_prompt(resume: dict, job: dict, rubric: list[dict]) -> str:
    """Construct the Claude prompt for resume scoring."""
    rubric_text = ""
    for r in rubric:
        rubric_text += f"\n### {r['criteria']} (Weight: {r['weight']})\n"
        for score, desc in r["descriptors"].items():
            rubric_text += f"  - Score {score}: {desc}\n"

    job_text = json.dumps(job, indent=2)

    return f"""You are an expert HR recruiter evaluating a candidate resume against a job description.
Score the candidate on each criterion using the rubric below.

## Job Description
{job_text}

## Candidate Resume
{resume['raw_text']}

## Scoring Rubric
For each criterion, assign a score from 1 to 5 using these guidelines:
{rubric_text}

## Instructions
Evaluate the candidate carefully and return ONLY a valid JSON object with this exact structure:
```json
{{
  "technical_skills_match": {{"score": <1-5>, "justification": "<brief reason>"}},
  "relevant_experience": {{"score": <1-5>, "justification": "<brief reason>"}},
  "education_alignment": {{"score": <1-5>, "justification": "<brief reason>"}},
  "communication_skills": {{"score": <1-5>, "justification": "<brief reason>"}},
  "leadership_experience": {{"score": <1-5>, "justification": "<brief reason>"}},
  "problem_solving": {{"score": <1-5>, "justification": "<brief reason>"}},
  "skill_gaps": ["<missing skill 1>", "<missing skill 2>"],
  "nice_to_have_matches": ["<matching nice-to-have 1>"],
  "overall_impression": "<2-3 sentence summary of candidate fit>"
}}
```

Return ONLY the JSON. No other text."""


def call_claude_for_scoring(prompt: str) -> dict:
    """Call Claude API and parse the JSON response."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    return _parse_json_response(raw_text)


def _parse_json_response(text: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    # Try to find JSON within ```json ... ``` fences
    fence_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    # Fallback: find first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


def evaluate_candidate(resume: dict, job: dict, rubric: list[dict]) -> dict:
    """Score a single resume against a job description with retry logic."""
    prompt = build_scoring_prompt(resume, job, rubric)

    for attempt in range(MAX_RETRIES + 1):
        try:
            time.sleep(API_DELAY_SECONDS)
            result = call_claude_for_scoring(prompt)
            return result
        except (json.JSONDecodeError, ValueError) as e:
            if attempt < MAX_RETRIES:
                print(f"\n    [RETRY {attempt + 1}] JSON parse error, retrying...")
                time.sleep(1 * (attempt + 1))
            else:
                print(f"\n    [ERROR] Failed to parse after {MAX_RETRIES + 1} attempts. Using defaults.")
                return _default_scores(str(e))
        except anthropic.APIError as e:
            if attempt < MAX_RETRIES:
                print(f"\n    [RETRY {attempt + 1}] API error: {e}, retrying...")
                time.sleep(2 * (attempt + 1))
            else:
                print(f"\n    [ERROR] API failed after {MAX_RETRIES + 1} attempts. Using defaults.")
                return _default_scores(str(e))


def _default_scores(error_msg: str) -> dict:
    """Return default mid-range scores when evaluation fails."""
    default = {"score": 3, "justification": "Could not evaluate - using default score"}
    return {
        "technical_skills_match": dict(default),
        "relevant_experience": dict(default),
        "education_alignment": dict(default),
        "communication_skills": dict(default),
        "leadership_experience": dict(default),
        "problem_solving": dict(default),
        "skill_gaps": [],
        "nice_to_have_matches": [],
        "overall_impression": f"Evaluation failed: {error_msg}",
        "parse_error": True,
    }
