"""
Scoring Engine Module
=====================
Applies rubric weights, computes final scores, ranks candidates, and classifies them.
"""

from datetime import datetime

from config import CRITERIA_KEY_MAP, TOP_CANDIDATE_SCORE_THRESHOLD


def compute_weighted_score(raw_scores: dict, rubric: list[dict]) -> float:
    """Apply rubric weights to raw criterion scores and return weighted total (1.0-5.0)."""
    weighted_sum = 0.0
    for entry in rubric:
        key = CRITERIA_KEY_MAP.get(entry["criteria"])
        if key and key in raw_scores:
            score = raw_scores[key]["score"]
            weighted_sum += score * entry["weight"]
    return weighted_sum


def classify_candidate(weighted_score: float, threshold: float = TOP_CANDIDATE_SCORE_THRESHOLD) -> str:
    """Return 'top_candidate' or 'not_selected' based on threshold."""
    return "top_candidate" if weighted_score >= threshold else "not_selected"


def rank_candidates_for_job(evaluations: list[dict]) -> list[dict]:
    """Sort evaluations by weighted_score descending and add rank field."""
    sorted_evals = sorted(evaluations, key=lambda e: e["weighted_score"], reverse=True)
    for i, ev in enumerate(sorted_evals, start=1):
        ev["rank"] = i
    return sorted_evals


def build_evaluation_report(all_evaluations: dict, jobs: list[dict] = None) -> dict:
    """Structure all results into a comprehensive JSON report."""
    report = {
        "generated_at": datetime.now().isoformat(),
        "threshold": TOP_CANDIDATE_SCORE_THRESHOLD,
        "jobs": {},
    }

    for job_id, evaluations in all_evaluations.items():
        job_title = ""
        if jobs:
            for j in jobs:
                if j["job_id"] == job_id:
                    job_title = j["title"]
                    break

        candidates = []
        for ev in evaluations:
            candidates.append(
                {
                    "name": ev["name"],
                    "email": ev.get("email", ""),
                    "rank": ev.get("rank", 0),
                    "weighted_score": ev["weighted_score"],
                    "classification": ev["classification"],
                    "raw_scores": {
                        k: v
                        for k, v in ev["raw_scores"].items()
                        if k not in ("skill_gaps", "nice_to_have_matches", "overall_impression", "parse_error")
                    },
                    "skill_gaps": ev["raw_scores"].get("skill_gaps", []),
                    "nice_to_have_matches": ev["raw_scores"].get("nice_to_have_matches", []),
                    "overall_impression": ev["raw_scores"].get("overall_impression", ""),
                }
            )

        top_count = sum(1 for c in candidates if c["classification"] == "top_candidate")

        report["jobs"][job_id] = {
            "title": job_title,
            "candidates": candidates,
            "top_candidate_count": top_count,
            "total_evaluated": len(candidates),
        }

    return report


def build_pipeline_summary(all_evaluations: dict, jobs: list[dict]) -> str:
    """Generate a human-readable text summary of the pipeline results."""
    lines = []
    lines.append("=" * 70)
    lines.append("CANDIDATE EVALUATION PIPELINE - SUMMARY REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Score Threshold for Interview: {TOP_CANDIDATE_SCORE_THRESHOLD} / 5.0")
    lines.append("=" * 70)

    total_top = 0
    total_evaluated = 0

    for job in jobs:
        job_id = job["job_id"]
        evals = all_evaluations.get(job_id, [])
        top = [e for e in evals if e["classification"] == "top_candidate"]
        rejected = [e for e in evals if e["classification"] == "not_selected"]

        total_top += len(top)
        total_evaluated += len(evals)

        lines.append(f"\n{'-' * 70}")
        lines.append(f"JOB: {job['title']} ({job_id})")
        lines.append(f"Department: {job['department']} | Level: {job['level']}")
        lines.append(f"Salary Range: {job['salary_range']}")
        lines.append(f"Candidates Evaluated: {len(evals)}")
        lines.append(f"Top Candidates: {len(top)} | Not Selected: {len(rejected)}")
        lines.append("")

        if top:
            lines.append("  TOP CANDIDATES (Advancing to Interview):")
            for e in top:
                lines.append(
                    f"    #{e['rank']}  {e['name']:<25s}  Score: {e['weighted_score']:.2f}"
                )
                gaps = e["raw_scores"].get("skill_gaps", [])
                if gaps:
                    lines.append(f"        Skill gaps: {', '.join(gaps[:3])}")
            lines.append("")

        if rejected:
            lines.append("  NOT SELECTED (Rejection Email Generated):")
            for e in rejected:
                lines.append(
                    f"    #{e['rank']}  {e['name']:<25s}  Score: {e['weighted_score']:.2f}"
                )

    lines.append(f"\n{'=' * 70}")
    lines.append("TOTALS")
    lines.append(f"  Total Evaluations: {total_evaluated}")
    lines.append(f"  Total Top Candidates: {total_top}")
    lines.append(f"  Total Rejections: {total_evaluated - total_top}")
    lines.append("=" * 70)

    return "\n".join(lines)
