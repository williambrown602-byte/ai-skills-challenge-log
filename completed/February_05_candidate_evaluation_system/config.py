from pathlib import Path

# --- Directories ---
PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"
REJECTION_DIR = OUTPUT_DIR / "rejection_emails"
PROFILE_DIR = OUTPUT_DIR / "interview_profiles"

# --- Data files (all co-located in project directory) ---
SAMPLE_RESUMES_PATH = PROJECT_DIR / "sample_resumes.txt"
ADDITIONAL_RESUMES_PATH = PROJECT_DIR / "additional_resumes.txt"
JOB_DESCRIPTIONS_PATH = PROJECT_DIR / "job_descriptions.json"
SCORING_RUBRIC_PATH = PROJECT_DIR / "scoring_rubric.csv"
INTERVIEW_TEMPLATE_PATH = PROJECT_DIR / "interview_template.json"
SALARY_BENCHMARKS_PATH = PROJECT_DIR / "salary_benchmarks.csv"

# --- LLM Settings ---
MODEL_NAME = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
API_DELAY_SECONDS = 0.5
MAX_RETRIES = 2

# --- Scoring ---
TOP_CANDIDATE_SCORE_THRESHOLD = 3.5  # out of 5.0 weighted score

# --- Criteria key mapping (rubric CSV names -> JSON keys) ---
CRITERIA_KEY_MAP = {
    "Technical Skills Match": "technical_skills_match",
    "Relevant Experience": "relevant_experience",
    "Education Alignment": "education_alignment",
    "Communication Skills": "communication_skills",
    "Leadership Experience": "leadership_experience",
    "Problem Solving": "problem_solving",
}
