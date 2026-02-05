"""
Profile Generator Module
========================
Generates interview-ready candidate profiles (top candidates) and
rejection email drafts (non-selected candidates) using Claude API.
"""

import json
import re
import time
from pathlib import Path

import anthropic

from config import (
    INTERVIEW_TEMPLATE_PATH,
    PROFILE_DIR,
    REJECTION_DIR,
    MODEL_NAME,
    MAX_TOKENS,
    API_DELAY_SECONDS,
    MAX_RETRIES,
)


def load_interview_template() -> dict:
    """Load the interview template JSON structure."""
    with open(INTERVIEW_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Interview Profile Generation
# ---------------------------------------------------------------------------

def build_interview_profile_prompt(
    resume: dict, job: dict, evaluation: dict, salary_benchmarks: dict, template: dict
) -> str:
    """Construct prompt for generating a filled interview profile."""
    # Find relevant salary benchmark
    salary_info = _find_salary_benchmark(job, salary_benchmarks)

    scores_summary = ""
    for key in ("technical_skills_match", "relevant_experience", "education_alignment",
                "communication_skills", "leadership_experience", "problem_solving"):
        entry = evaluation["raw_scores"].get(key, {})
        if isinstance(entry, dict):
            scores_summary += f"  - {key}: {entry.get('score', 'N/A')}/5 - {entry.get('justification', '')}\n"

    skill_gaps = evaluation["raw_scores"].get("skill_gaps", [])
    nice_to_haves = evaluation["raw_scores"].get("nice_to_have_matches", [])

    template_json = json.dumps(template, indent=2)
    job_json = json.dumps(job, indent=2)

    return f"""You are an expert HR interview preparation specialist.
Generate a comprehensive interview-ready candidate profile.

## Candidate Resume
{resume['raw_text']}

## Job Description
{job_json}

## Evaluation Scores
{scores_summary}
Weighted Score: {evaluation['weighted_score']}/5.0
Skill Gaps: {', '.join(skill_gaps) if skill_gaps else 'None identified'}
Nice-to-Have Matches: {', '.join(nice_to_haves) if nice_to_haves else 'None'}

## Salary Benchmark Data
{salary_info}

## Instructions
Fill in the following template with specific, actionable content.
Each list field should have 3-5 items. Be specific to this candidate and role.

Template structure:
{template_json}

Return ONLY a valid JSON object matching the template structure with all fields populated.
```json
"""


def generate_interview_profile(
    resume: dict, job: dict, evaluation: dict, salary_benchmarks: dict, template: dict
) -> dict:
    """Generate a filled interview profile for a top candidate."""
    prompt = build_interview_profile_prompt(resume, job, evaluation, salary_benchmarks, template)
    client = anthropic.Anthropic()

    for attempt in range(MAX_RETRIES + 1):
        try:
            time.sleep(API_DELAY_SECONDS)
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = response.content[0].text
            profile = _parse_json_response(raw_text)

            # Wrap in metadata
            return {
                "candidate_name": resume["name"],
                "candidate_email": resume["email"],
                "job_id": job["job_id"],
                "job_title": job["title"],
                "weighted_score": evaluation["weighted_score"],
                "profile": profile,
            }
        except (json.JSONDecodeError, ValueError) as e:
            if attempt < MAX_RETRIES:
                print(f"    [RETRY {attempt + 1}] Profile JSON parse error, retrying...")
                time.sleep(1 * (attempt + 1))
            else:
                print(f"    [ERROR] Profile generation failed: {e}")
                return _fallback_profile(resume, job, evaluation)
        except anthropic.APIError as e:
            if attempt < MAX_RETRIES:
                print(f"    [RETRY {attempt + 1}] API error: {e}, retrying...")
                time.sleep(2 * (attempt + 1))
            else:
                print(f"    [ERROR] Profile API call failed: {e}")
                return _fallback_profile(resume, job, evaluation)


def save_interview_profile(profile: dict, candidate_name: str, job_id: str) -> Path:
    """Save interview profile as JSON file."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = candidate_name.replace(" ", "_").replace(".", "")
    filename = f"{job_id}_{safe_name}.json"
    path = PROFILE_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    return path


# ---------------------------------------------------------------------------
# Rejection Email Generation
# ---------------------------------------------------------------------------

def build_rejection_email_prompt(resume: dict, job: dict, evaluation: dict) -> str:
    """Construct prompt for generating a rejection email."""
    skill_gaps = evaluation["raw_scores"].get("skill_gaps", [])

    # Find strongest areas
    best_criteria = []
    for key in ("technical_skills_match", "relevant_experience", "education_alignment",
                "communication_skills", "leadership_experience", "problem_solving"):
        entry = evaluation["raw_scores"].get(key, {})
        if isinstance(entry, dict) and entry.get("score", 0) >= 4:
            best_criteria.append(key.replace("_", " ").title())

    return f"""You are a professional HR communications specialist.
Write a rejection email for a candidate who was not selected.

## Candidate
Name: {resume['name']}
Position Applied For: {job['title']} ({job['department']} department)

## Context
- Skill gaps identified: {', '.join(skill_gaps) if skill_gaps else 'General fit concerns'}
- Strongest areas: {', '.join(best_criteria) if best_criteria else 'Multiple areas showed promise'}

## Requirements
- Address the candidate by first name
- Reference the specific position
- Be professional, warm, and empathetic
- Include 1-2 specific areas they could strengthen (based on skill gaps)
- Encourage future applications
- Do NOT reveal specific scores or rankings
- Keep it under 200 words
- Include a subject line at the top
- Sign off as "The Hiring Team"

Write the complete email now:"""


def generate_rejection_email(resume: dict, job: dict, evaluation: dict) -> str:
    """Generate a personalized rejection email for a non-selected candidate."""
    prompt = build_rejection_email_prompt(resume, job, evaluation)
    client = anthropic.Anthropic()

    for attempt in range(MAX_RETRIES + 1):
        try:
            time.sleep(API_DELAY_SECONDS)
            response = client.messages.create(
                model=MODEL_NAME,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except anthropic.APIError as e:
            if attempt < MAX_RETRIES:
                print(f"    [RETRY {attempt + 1}] API error: {e}, retrying...")
                time.sleep(2 * (attempt + 1))
            else:
                print(f"    [ERROR] Rejection email failed: {e}")
                return _fallback_rejection_email(resume, job)


def save_rejection_email(email_text: str, candidate_name: str, job_id: str) -> Path:
    """Save rejection email as a .txt file."""
    REJECTION_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = candidate_name.replace(" ", "_").replace(".", "")
    filename = f"{job_id}_{safe_name}_rejection.txt"
    path = REJECTION_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write(email_text)
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_response(text: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    fence_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        return json.loads(fence_match.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start : end + 1])

    raise ValueError(f"Could not parse JSON from response: {text[:200]}")


def _find_salary_benchmark(job: dict, benchmarks: dict) -> str:
    """Look up salary benchmark for a job's position and level."""
    # Try to match job title to benchmark position names
    title_lower = job["title"].lower()
    level = job.get("level", "Mid-level")

    level_map = {"Senior": "Senior", "Mid-level": "Mid", "Junior": "Junior"}
    bench_level = level_map.get(level, "Mid")

    for (position, blevel), data in benchmarks.items():
        if position.lower() in title_lower or title_lower in position.lower():
            if blevel == bench_level:
                return (
                    f"Position: {position} ({blevel})\n"
                    f"Market Range: ${data['min']:,} - ${data['max']:,}\n"
                    f"Median: ${data['median']:,}\n"
                    f"Market Trend: {data['trend']}\n"
                    f"Job Posting Range: {job.get('salary_range', 'N/A')}"
                )

    return f"No exact benchmark match found. Job Posting Range: {job.get('salary_range', 'N/A')}"


def _fallback_profile(resume: dict, job: dict, evaluation: dict) -> dict:
    """Return a minimal profile when API generation fails."""
    return {
        "candidate_name": resume["name"],
        "candidate_email": resume["email"],
        "job_id": job["job_id"],
        "job_title": job["title"],
        "weighted_score": evaluation["weighted_score"],
        "profile": {
            "interview_template": {
                "candidate_summary": {
                    "strengths": [f"Scored {evaluation['weighted_score']:.2f}/5.0 overall"],
                    "concerns": evaluation["raw_scores"].get("skill_gaps", []),
                    "culture_fit_indicators": ["Requires manual assessment"],
                    "salary_expectation_alignment": "Review needed",
                },
                "technical_assessment": {
                    "skill_verification_questions": ["Verify core technical skills listed on resume"],
                    "scenario_based_questions": ["Present a relevant technical scenario"],
                    "hands_on_exercise_suggestions": ["Assign a role-appropriate exercise"],
                },
                "behavioral_questions": {
                    "leadership_examples": ["Describe a time you led a team"],
                    "problem_solving_scenarios": ["Walk through a challenging problem you solved"],
                    "communication_assessment": ["Explain a technical concept to a non-technical audience"],
                    "teamwork_evaluation": ["Describe a successful team collaboration"],
                },
                "role_specific_topics": {
                    "key_discussion_points": ["Discuss relevant domain experience"],
                    "project_examples_to_explore": ["Elaborate on key resume projects"],
                    "growth_potential_areas": ["Discuss career growth goals"],
                },
                "next_steps": {
                    "recommended_interview_panel": ["Hiring manager", "Technical lead"],
                    "additional_assessments_needed": ["Technical assessment"],
                    "reference_check_focus_areas": ["Verify employment history"],
                },
            }
        },
        "generation_note": "Fallback profile - API generation failed",
    }


def _fallback_rejection_email(resume: dict, job: dict) -> str:
    """Return a generic rejection email when API generation fails."""
    first_name = resume["name"].split()[0]
    return f"""Subject: Update on Your Application - {job['title']} Position

Dear {first_name},

Thank you for taking the time to apply for the {job['title']} position in our {job['department']} department. We appreciate your interest in joining our team.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely align with our current needs for this role.

We encourage you to continue developing your skills and to consider applying for future opportunities with us that may be a better match for your experience.

We wish you all the best in your career journey.

Warm regards,
The Hiring Team"""
