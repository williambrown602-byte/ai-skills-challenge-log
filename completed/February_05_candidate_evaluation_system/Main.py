"""
Candidate Resume Evaluation System
====================================
Automated pipeline that:
  1. Parses resumes from text (and optionally PDF) files
  2. Scores each resume against job descriptions using Claude API
  3. Ranks and classifies candidates as top/not-selected
  4. Generates interview-ready profiles for top candidates
  5. Generates rejection email drafts for non-selected candidates
  6. Produces a comprehensive evaluation report

Usage:
    python Main.py                    # Evaluate all resumes against all jobs
    python Main.py --job JD001        # Evaluate against a specific job only
    python Main.py --dry-run          # Parse and display data without API calls
"""

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()  # Load .env file (keeps API key out of source code)

from config import OUTPUT_DIR, REJECTION_DIR, PROFILE_DIR, TOP_CANDIDATE_SCORE_THRESHOLD
from resume_parser import load_all_resumes
from job_matcher import (
    load_job_descriptions,
    load_scoring_rubric,
    load_salary_benchmarks,
    evaluate_candidate,
)
from scoring_engine import (
    compute_weighted_score,
    classify_candidate,
    rank_candidates_for_job,
    build_evaluation_report,
    build_pipeline_summary,
)
from profile_generator import (
    load_interview_template,
    generate_interview_profile,
    generate_rejection_email,
    save_interview_profile,
    save_rejection_email,
)


def ensure_output_dirs():
    """Create output directory structure."""
    for d in [OUTPUT_DIR, REJECTION_DIR, PROFILE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def phase_1_load(job_filter: str = None):
    """Phase 1: Load and parse all input data."""
    print("=" * 60)
    print("PHASE 1: LOADING DATA")
    print("=" * 60)

    resumes = load_all_resumes()
    print(f"  Loaded {len(resumes)} resumes")
    for r in resumes:
        print(f"    - {r['name']} ({r['total_years_experience']}yr exp, {len(r['skills'])} skills)")

    jobs = load_job_descriptions()
    if job_filter:
        jobs = [j for j in jobs if j["job_id"] == job_filter]
        if not jobs:
            print(f"  [ERROR] No job found with ID '{job_filter}'")
            sys.exit(1)
    print(f"  Loaded {len(jobs)} job description(s)")
    for j in jobs:
        print(f"    - {j['job_id']}: {j['title']} ({j['level']})")

    rubric = load_scoring_rubric()
    print(f"  Loaded scoring rubric ({len(rubric)} criteria)")

    template = load_interview_template()
    print(f"  Loaded interview template")

    benchmarks = load_salary_benchmarks()
    print(f"  Loaded salary benchmarks ({len(benchmarks)} entries)")

    return resumes, jobs, rubric, template, benchmarks


def phase_2_evaluate(resumes, jobs, rubric):
    """Phase 2: Score every resume against target jobs using Claude API."""
    print("\n" + "=" * 60)
    print("PHASE 2: EVALUATING CANDIDATES VIA CLAUDE API")
    print("=" * 60)

    all_evaluations = {}
    total = len(resumes) * len(jobs)
    count = 0

    for job in jobs:
        job_id = job["job_id"]
        all_evaluations[job_id] = []

        print(f"\n  --- {job['title']} ({job_id}) ---")

        for resume in resumes:
            count += 1
            print(f"  [{count}/{total}] Evaluating {resume['name']}...", end=" ", flush=True)

            raw_scores = evaluate_candidate(resume, job, rubric)
            weighted = compute_weighted_score(raw_scores, rubric)
            classification = classify_candidate(weighted)

            evaluation = {
                "name": resume["name"],
                "email": resume["email"],
                "raw_scores": raw_scores,
                "weighted_score": round(weighted, 2),
                "classification": classification,
                "resume": resume,
            }
            all_evaluations[job_id].append(evaluation)

            status = "TOP" if classification == "top_candidate" else "---"
            print(f"Score: {weighted:.2f} [{status}]")

    return all_evaluations


def phase_3_rank(all_evaluations, jobs):
    """Phase 3: Rank candidates per job and display results."""
    print("\n" + "=" * 60)
    print("PHASE 3: RANKING CANDIDATES")
    print("=" * 60)

    for job in jobs:
        job_id = job["job_id"]
        ranked = rank_candidates_for_job(all_evaluations[job_id])
        all_evaluations[job_id] = ranked

        top = [e for e in ranked if e["classification"] == "top_candidate"]
        not_selected = [e for e in ranked if e["classification"] == "not_selected"]

        print(f"\n  {job['title']} ({job_id})")
        print(f"  Top Candidates: {len(top)} | Not Selected: {len(not_selected)}")
        print()
        for e in ranked:
            marker = " *** TOP ***" if e["classification"] == "top_candidate" else ""
            print(f"    #{e['rank']:2d}  {e['name']:<25s}  {e['weighted_score']:.2f}{marker}")

    return all_evaluations


def phase_4_profiles(all_evaluations, jobs, template, benchmarks):
    """Phase 4: Generate interview profiles for top candidates."""
    print("\n" + "=" * 60)
    print("PHASE 4: GENERATING INTERVIEW PROFILES")
    print("=" * 60)

    profile_count = 0
    for job in jobs:
        job_id = job["job_id"]
        top_candidates = [
            e for e in all_evaluations[job_id] if e["classification"] == "top_candidate"
        ]

        if not top_candidates:
            print(f"\n  {job['title']}: No top candidates to profile.")
            continue

        for eval_entry in top_candidates:
            print(f"  Generating profile: {eval_entry['name']} for {job['title']}...", flush=True)
            profile = generate_interview_profile(
                eval_entry["resume"], job, eval_entry, benchmarks, template
            )
            path = save_interview_profile(profile, eval_entry["name"], job_id)
            print(f"    -> Saved: {path.name}")
            profile_count += 1

    print(f"\n  Total interview profiles generated: {profile_count}")


def phase_5_rejections(all_evaluations, jobs):
    """Phase 5: Generate rejection email drafts for non-selected candidates."""
    print("\n" + "=" * 60)
    print("PHASE 5: GENERATING REJECTION EMAILS")
    print("=" * 60)

    email_count = 0
    for job in jobs:
        job_id = job["job_id"]
        rejected = [
            e for e in all_evaluations[job_id] if e["classification"] == "not_selected"
        ]

        if not rejected:
            print(f"\n  {job['title']}: All candidates are top candidates!")
            continue

        for eval_entry in rejected:
            print(f"  Generating rejection: {eval_entry['name']} for {job['title']}...", flush=True)
            email = generate_rejection_email(eval_entry["resume"], job, eval_entry)
            path = save_rejection_email(email, eval_entry["name"], job_id)
            print(f"    -> Saved: {path.name}")
            email_count += 1

    print(f"\n  Total rejection emails generated: {email_count}")


def phase_6_report(all_evaluations, jobs):
    """Phase 6: Save final evaluation report and pipeline summary."""
    print("\n" + "=" * 60)
    print("PHASE 6: GENERATING REPORTS")
    print("=" * 60)

    # Build and save JSON report (strip resume raw data for cleanliness)
    report = build_evaluation_report(all_evaluations, jobs)
    report_path = OUTPUT_DIR / "evaluation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Saved evaluation report: {report_path.name}")

    # Build and save text summary
    summary = build_pipeline_summary(all_evaluations, jobs)
    summary_path = OUTPUT_DIR / "pipeline_summary.txt"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"  Saved pipeline summary: {summary_path.name}")

    # Print summary to console
    print("\n" + summary)


def dry_run(resumes, jobs, rubric):
    """Display parsed data without making API calls."""
    print("\n" + "=" * 60)
    print("DRY RUN - No API calls will be made")
    print("=" * 60)

    print(f"\n  {len(resumes)} Resumes Parsed:")
    for r in resumes:
        print(f"    {r['name']}")
        print(f"      Email: {r['email']}")
        print(f"      Experience: {r['total_years_experience']} years")
        print(f"      Skills: {', '.join(r['skills'])}")
        print(f"      Positions: {len(r['experience_entries'])}")
        for exp in r["experience_entries"]:
            print(f"        - {exp['title']} at {exp['company']} ({exp['years']})")

    print(f"\n  {len(jobs)} Jobs to Match Against:")
    for j in jobs:
        print(f"    {j['job_id']}: {j['title']}")
        print(f"      Required skills: {', '.join(j['requirements']['technical_skills'])}")
        print(f"      Experience: {j['requirements']['experience_years']}+ years")

    print(f"\n  {len(rubric)} Scoring Criteria:")
    for r in rubric:
        print(f"    {r['criteria']} (weight: {r['weight']})")

    print(f"\n  Total evaluations that would be performed: {len(resumes) * len(jobs)}")


def main():
    parser = argparse.ArgumentParser(description="Candidate Resume Evaluation System")
    parser.add_argument("--job", type=str, help="Evaluate against a specific job ID only (e.g., JD001)")
    parser.add_argument("--dry-run", action="store_true", help="Parse data and display without API calls")
    args = parser.parse_args()

    print()
    print("*" * 60)
    print("   CANDIDATE RESUME EVALUATION SYSTEM")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("*" * 60)

    ensure_output_dirs()

    resumes, jobs, rubric, template, benchmarks = phase_1_load(job_filter=args.job)

    if args.dry_run:
        dry_run(resumes, jobs, rubric)
        return

    # Verify API key is available before making calls
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n  [ERROR] ANTHROPIC_API_KEY environment variable is not set.")
        print("  Set it with:  set ANTHROPIC_API_KEY=your-key-here  (Windows)")
        print("  Or:           export ANTHROPIC_API_KEY=your-key-here (Linux/Mac)")
        sys.exit(1)

    all_evaluations = phase_2_evaluate(resumes, jobs, rubric)
    all_evaluations = phase_3_rank(all_evaluations, jobs)
    phase_4_profiles(all_evaluations, jobs, template, benchmarks)
    phase_5_rejections(all_evaluations, jobs)
    phase_6_report(all_evaluations, jobs)

    print("\n" + "*" * 60)
    print("   PIPELINE COMPLETE")
    print("*" * 60)


if __name__ == "__main__":
    main()
