"""
Resume Parser Module
====================
Extracts and structures candidate data from .txt (and optionally PDF) resume files.
"""

import re
from pathlib import Path

from config import SAMPLE_RESUMES_PATH, ADDITIONAL_RESUMES_PATH


def load_resumes_from_txt(file_path: Path) -> list[dict]:
    """Read a .txt file containing multiple resumes separated by '---'."""
    text = file_path.read_text(encoding="utf-8")
    raw_blocks = re.split(r"\n-{3,}\n", text)
    resumes = []
    for block in raw_blocks:
        block = block.strip()
        if block:
            parsed = parse_single_resume(block)
            if parsed["name"]:
                resumes.append(parsed)
    return resumes


def parse_single_resume(raw_text: str) -> dict:
    """Extract structured fields from a single resume text block."""
    resume = {
        "name": "",
        "email": "",
        "phone": "",
        "raw_text": raw_text,
        "experience_entries": [],
        "education": [],
        "skills": [],
        "total_years_experience": 0,
    }

    # --- Contact info ---
    name_match = re.search(r"Name:\s*(.+)", raw_text)
    if name_match:
        resume["name"] = name_match.group(1).strip()

    email_match = re.search(r"Email:\s*(.+)", raw_text)
    if email_match:
        resume["email"] = email_match.group(1).strip()

    phone_match = re.search(r"Phone:\s*(.+)", raw_text)
    if phone_match:
        resume["phone"] = phone_match.group(1).strip()

    # --- Section splitting ---
    experience_text = _extract_section(raw_text, "EXPERIENCE", "EDUCATION")
    education_text = _extract_section(raw_text, "EDUCATION", "SKILLS")
    skills_text = _extract_section(raw_text, "SKILLS", None)

    # --- Parse experience entries ---
    if experience_text:
        resume["experience_entries"] = _parse_experience(experience_text)
        resume["total_years_experience"] = _calculate_total_years(
            resume["experience_entries"]
        )

    # --- Parse education ---
    if education_text:
        resume["education"] = [
            line.strip()
            for line in education_text.strip().split("\n")
            if line.strip()
        ]

    # --- Parse skills ---
    if skills_text:
        resume["skills"] = [s.strip() for s in skills_text.split(",") if s.strip()]

    return resume


def _extract_section(text: str, start_header: str, end_header: str | None) -> str:
    """Extract text between two section headers."""
    pattern_start = rf"{start_header}:\s*\n"
    match_start = re.search(pattern_start, text)
    if not match_start:
        return ""

    start_pos = match_start.end()

    if end_header:
        pattern_end = rf"\n{end_header}:\s*\n"
        match_end = re.search(pattern_end, text[start_pos:])
        if match_end:
            return text[start_pos : start_pos + match_end.start()]

    return text[start_pos:]


def _parse_experience(exp_text: str) -> list[dict]:
    """Parse experience section into structured entries."""
    entries = []
    # Match lines like: "Senior Software Developer, TechCorp (2020-2024)"
    header_pattern = re.compile(
        r"^(.+?),\s*(.+?)\s*\((\d{4})\s*-\s*(\d{4})\)", re.MULTILINE
    )

    headers = list(header_pattern.finditer(exp_text))

    for i, match in enumerate(headers):
        title = match.group(1).strip()
        company = match.group(2).strip()
        start_year = int(match.group(3))
        end_year = int(match.group(4))

        # Get bullets between this header and the next (or end of text)
        bullet_start = match.end()
        bullet_end = headers[i + 1].start() if i + 1 < len(headers) else len(exp_text)
        bullet_text = exp_text[bullet_start:bullet_end]

        bullets = [
            line.strip().lstrip("- ").strip()
            for line in bullet_text.split("\n")
            if line.strip().startswith("-")
        ]

        entries.append(
            {
                "title": title,
                "company": company,
                "years": f"{start_year}-{end_year}",
                "duration": end_year - start_year,
                "bullets": bullets,
            }
        )

    return entries


def _calculate_total_years(entries: list[dict]) -> int:
    """Sum up total years of experience from all entries."""
    return sum(entry["duration"] for entry in entries)


def load_all_resumes() -> list[dict]:
    """Load and parse resumes from both resume files."""
    resumes = []

    if SAMPLE_RESUMES_PATH.exists():
        resumes.extend(load_resumes_from_txt(SAMPLE_RESUMES_PATH))

    if ADDITIONAL_RESUMES_PATH.exists():
        resumes.extend(load_resumes_from_txt(ADDITIONAL_RESUMES_PATH))

    return resumes


def load_resume_from_pdf(file_path: Path) -> dict | None:
    """Extract text from a PDF file and parse it as a resume."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(file_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return parse_single_resume(text)
    except ImportError:
        print("  [WARNING] PyPDF2 not installed. Skipping PDF parsing.")
        return None


if __name__ == "__main__":
    resumes = load_all_resumes()
    for r in resumes:
        print(f"{r['name']} | {r['total_years_experience']}yr | Skills: {', '.join(r['skills'][:5])}...")
