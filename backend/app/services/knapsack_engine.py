"""
Knapsack Engine — 0/1 Knapsack Dynamic Programming

Generates a mathematically optimal X-day remediation plan by treating:
  - Each failed skill as an "item" with a time cost (weight) and hiring ROI (value).
  - The candidate's available study hours as the knapsack capacity.

The DP algorithm selects the exact subset of skills that maximizes hireability
within the candidate's time budget. The LLM is only used to format the output
into readable English — it has zero control over the study plan's logic.

Also includes Section-Weighted Term Frequency for extracting skill priorities
from a Job Description without using an LLM.
"""
import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Load Skill Metadata ────────────────────────────────────────────────────

_SKILL_DB: Optional[Dict[str, int]] = None
_SKILL_DB_LOWER: Optional[Dict[str, int]] = None


def _load_skill_db() -> Dict[str, int]:
    """Load the static skill knowledge base from skill_metadata.json."""
    global _SKILL_DB, _SKILL_DB_LOWER
    if _SKILL_DB is not None:
        return _SKILL_DB

    json_path = os.path.join(os.path.dirname(__file__), "..", "utils", "skill_metadata.json")
    json_path = os.path.normpath(json_path)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            _SKILL_DB = json.load(f)
        _SKILL_DB_LOWER = {k.lower(): v for k, v in _SKILL_DB.items()}
        logger.info(f"[KNAPSACK] Loaded {len(_SKILL_DB)} skills from knowledge base.")
    except FileNotFoundError:
        logger.error(f"[KNAPSACK ERROR] skill_metadata.json not found at {json_path}")
        _SKILL_DB = {}
        _SKILL_DB_LOWER = {}

    return _SKILL_DB


def get_skill_time_cost(skill_name: str, default: int = 6) -> int:
    """
    Get the estimated learning hours for a skill from the static knowledge base.
    Falls back to a default value if the skill is not found.
    No LLM involved — fully deterministic.
    """
    _load_skill_db()
    return _SKILL_DB_LOWER.get(skill_name.lower().strip(), default)


# ─── Section-Weighted Term Frequency ────────────────────────────────────────

# Keywords that indicate "Required" vs "Nice to Have" sections in a JD
REQUIRED_SECTION_MARKERS = [
    r"(?i)\b(required|requirements|must.?have|mandatory|essential|minimum|qualifications|responsibilities|day.?to.?day)\b",
]
OPTIONAL_SECTION_MARKERS = [
    r"(?i)\b(nice.?to.?have|preferred|bonus|plus|desirable|good.?to.?have|optional)\b",
]


def extract_skill_priorities(jd_text: str) -> Dict[str, float]:
    """
    Section-Weighted Term Frequency — extracts skill priorities from a single
    Job Description using pure math (no LLM).

    1. Splits the JD into lines.
    2. Tracks which "section" each line is in (Required=3x, NiceToHave=1x, Default=2x).
    3. For each known skill, counts occurrences weighted by section.

    Returns: {skill_name: priority_score}  (higher = more important to the employer)
    """
    _load_skill_db()
    if not _SKILL_DB_LOWER or not jd_text.strip():
        return {}

    lines = jd_text.split("\n")
    current_multiplier = 2.0  # Default section weight

    skill_scores: Dict[str, float] = {}
    jd_lower = jd_text.lower()

    # First pass: figure out if specific skills appear in the JD at all
    for skill_name in _SKILL_DB_LOWER:
        # Use word boundary matching to avoid partial matches
        pattern = r"\b" + re.escape(skill_name) + r"\b"
        matches = re.findall(pattern, jd_lower)
        if matches:
            skill_scores[skill_name] = 0.0

    if not skill_scores:
        return {}

    # Second pass: walk through lines tracking section context
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this line is a section header
        for pat in REQUIRED_SECTION_MARKERS:
            if re.search(pat, line_stripped):
                current_multiplier = 3.0
                break
        for pat in OPTIONAL_SECTION_MARKERS:
            if re.search(pat, line_stripped):
                current_multiplier = 1.0
                break

        line_lower = line_stripped.lower()
        for skill_name in list(skill_scores.keys()):
            pattern = r"\b" + re.escape(skill_name) + r"\b"
            count = len(re.findall(pattern, line_lower))
            if count > 0:
                skill_scores[skill_name] += count * current_multiplier

    # Filter out zero-score skills
    return {k: v for k, v in skill_scores.items() if v > 0}


# ─── 0/1 Knapsack DP ────────────────────────────────────────────────────────

def knapsack_remediation(
    failed_skills: List[str],
    jd_text: str = "",
    total_hours: int = 20,
    num_days: int = 7,
) -> Dict:
    """
    0/1 Knapsack Dynamic Programming — generates the mathematically optimal
    study plan for a candidate with limited time.

    Parameters:
        failed_skills: List of skill names the candidate failed during the interview.
        jd_text:       The full Job Description text (for Section-Weighted TF priority).
        total_hours:   Total study hours available (knapsack capacity).
        num_days:      Number of days to distribute the study plan across.

    Returns:
        {
            "selected_skills": [{"skill": str, "hours": int, "priority": float, "day": int}],
            "dropped_skills":  [{"skill": str, "hours": int, "reason": str}],
            "total_hours_used": int,
            "total_roi_score": float,
            "budget_hours": int,
            "num_days": int,
        }
    """
    if not failed_skills:
        return {
            "selected_skills": [],
            "dropped_skills": [],
            "total_hours_used": 0,
            "total_roi_score": 0,
            "budget_hours": total_hours,
            "num_days": num_days,
        }

    # Get priorities from JD using Section-Weighted TF
    jd_priorities = extract_skill_priorities(jd_text) if jd_text else {}

    # Build items list: each item = (skill_name, weight=hours, value=priority)
    items = []
    for skill in failed_skills:
        weight = get_skill_time_cost(skill)
        # Value = JD priority (if found), else a base value of 5.0
        value = jd_priorities.get(skill.lower().strip(), 5.0)
        items.append((skill, weight, value))

    n = len(items)
    capacity = total_hours

    # DP Table: dp[i][w] = max value using first i items with capacity w
    dp = [[0.0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        _, weight, value = items[i - 1]
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]  # Don't take item i
            if weight <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weight] + value)

    # Backtrack to find which items were selected
    selected_indices = []
    w = capacity
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:
            selected_indices.append(i - 1)
            w -= items[i - 1][1]

    selected_indices.reverse()

    # Build the selected skills list with day assignments
    selected_skills = []
    dropped_skills = []
    total_hours_used = 0

    for idx in selected_indices:
        skill_name, hours, priority = items[idx]
        selected_skills.append({
            "skill": skill_name,
            "hours": hours,
            "priority": round(priority, 1),
        })
        total_hours_used += hours

    # Assign days proportionally
    if selected_skills:
        hours_per_day = max(1, total_hours_used // num_days)
        current_day = 1
        day_hours = 0
        for skill_entry in selected_skills:
            skill_entry["day"] = current_day
            day_hours += skill_entry["hours"]
            if day_hours >= hours_per_day and current_day < num_days:
                current_day += 1
                day_hours = 0

    # Identify dropped skills (those NOT selected by the knapsack)
    selected_set = set(selected_indices)
    for idx in range(n):
        if idx not in selected_set:
            skill_name, hours, priority = items[idx]
            dropped_skills.append({
                "skill": skill_name,
                "hours": hours,
                "reason": f"Requires {hours}h but exceeds remaining budget. ROI priority: {round(priority, 1)}",
            })

    total_roi = dp[n][capacity]

    logger.info(
        f"[KNAPSACK] Selected {len(selected_skills)}/{n} skills, "
        f"using {total_hours_used}/{total_hours}h, ROI={round(total_roi, 1)}"
    )

    return {
        "selected_skills": selected_skills,
        "dropped_skills": dropped_skills,
        "total_hours_used": total_hours_used,
        "total_roi_score": round(total_roi, 1),
        "budget_hours": total_hours,
        "num_days": num_days,
    }
