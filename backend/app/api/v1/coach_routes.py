"""
Coach Routes — BYOK Multi-Provider Interview & Analytics API.

Endpoints:
  POST /test-key     — Verify API key works
  POST /init         — Initialize coaching session
  POST /chat         — Multi-turn chat
  POST /scorecard    — Mid-session scorecard
  POST /end-report   — Final report with DP Knapsack remediation plan
  POST /analytics    — Structured analytics JSON for Dashboard
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
import logging
import re
import json

from app.utils.auth import get_current_user
from app.database_models import User, VivaSession
from app.database import get_db
from sqlalchemy.orm import Session
from app.services.coach_service import test_api_key_sync, call_llm_sync, build_system_prompt
from app.services.knapsack_engine import knapsack_remediation, extract_skill_priorities

logger = logging.getLogger(__name__)
router = APIRouter()

# ─── Request Schemas ─────────────────────────────────────────────────────────

class TestKeyRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None

class InitCoachRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    mode: str
    role: str
    level: str
    jd: Optional[str] = None
    resume: Optional[str] = None
    num_questions: int = 5

class BatchEvaluateRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    mode_name: str
    role: str
    level_name: str
    jd: Optional[str] = None
    resume: Optional[str] = None
    qa_pairs: List[Dict[str, str]]
    elapsed: str
    study_hours: Optional[int] = 20
    study_days: Optional[int] = 7

class ChatCoachRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    system_prompt: Optional[str] = None

class ScorecardRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    elapsed: str
    question_num: int
    system_prompt: Optional[str] = None

class EndReportRequest(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None
    messages: List[Dict[str, Any]]
    mode_name: str
    role: str
    level_name: str
    elapsed: str
    question_num: int
    jd: Optional[str] = None
    resume: Optional[str] = None
    system_prompt: Optional[str] = None
    study_hours: Optional[int] = 20
    study_days: Optional[int] = 7

class AnalyticsRequest(BaseModel):
    report_text: str
    mode_name: str
    role: str
    level_name: str
    elapsed: str
    question_num: int
    jd: Optional[str] = None
    resume: Optional[str] = None
    study_hours: Optional[int] = 20
    study_days: Optional[int] = 7
    messages: Optional[List[Dict[str, Any]]] = None

# ─── Mode-Specific Report Templates ─────────────────────────────────────────

MODE_REPORT_PROMPTS = {
    "behavioral": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| STAR Method Adherence & Structure | /20 | |
| Quantifiable Metrics & Business Impact | /20 | |
| Leadership Adroitness & Influence | /20 | |
| Extreme Ownership & Failure Recovery | /20 | |
| Executive Presence & Communication | /20 | |

### ⭐ STAR Narrative Deconstruction
| Question / Topic | Situation & Task | Action Taken | Result & Metric | Critique |
|---|---|---|---|---|
| [Topic 1] | | | | |
| [Topic 2] | | | | |""",

    "technical": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| Algorithmic Correctness & Edge-Cases | /20 | |
| Big-O Time & Space Complexity | /20 | |
| Code Cleanliness & Modular Structure | /20 | |
| Optimization & Architectural Tradeoffs | /20 | |
| Production Debugging & Mastery | /20 | |

### 💻 Code Review & Suboptimal Snippet Deconstruction
- **Suboptimal Snippet Identified:** `[Code or logic flaw]`
- **Deconstruction:** [Why it breaks or wastes resources]
- **Production Optimal Refactor:**
```python
# Refactored production grade implementation
```""",

    "system-design": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| Scale Assumptions & Capacity Math | /20 | |
| High-Level Architecture & API Design | /20 | |
| Sharding, Caching & Partitioning | /20 | |
| Fault Tolerance & Bottleneck Audit | /20 | |
| Network Latency & Scalability Tradeoffs | /20 | |

### 🏛️ Architecture Bottleneck & Tradeoff Matrix
- **Bottlenecks Identified:** [Single points of failure, hot shards, unindexed reads]
- **Caching & Consistency Strategy:** [Write-back vs Write-through, Eventual consistency analysis]
- **Horizontal Scalability Verdict:** [How this architecture holds up at 100x traffic]""",

    "assessment": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| Rapid Problem Comprehension | /20 | |
| Quantitative & Logical Deduction | /20 | |
| Execution Speed Under Strict Limits | /20 | |
| Boundary & Corner-Case Trapping | /20 | |
| Pattern Recognition & Shortcuts | /20 | |

### ⏱️ Timed Question Audit Scorecard
| Question # | Problem Focus | Candidate Answer | Optimal Solution | Verdict |
|---|---|---|---|---|
| Q1 | | | | [🟢 PASS / 🔴 FAIL] |
| Q2 | | | | [🟢 PASS / 🔴 FAIL] |""",

    "certification": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| Exam Blueprint & Domain Mastery | /20 | |
| Multi-Choice Elimination Precision | /20 | |
| Architectural Framework Compliance | /20 | |
| Scenario Root-Cause Deduction | /20 | |
| Benchmark Exam Passing Readiness | /20 | |

### 📋 Domain Knowledge Audit
- **Mastered Domains:** [Blueprint domains ready for exam]
- **Vulnerable Domains:** [Areas requiring immediate re-reading]
- **Exam Readiness Benchmark:** [Estimated chance of passing real certification exam today]""",

    "case-study": """### Competency Matrix Breakdown
| Evaluation Dimension | Score | Executive Critique |
|---|---|---|
| MECE Framework Decomposition | /20 | |
| First-Principles Business Acumen | /20 | |
| Unit Economics & Mental Math | /20 | |
| Strategic Feasibility & Risks | /20 | |
| Executive Synthesis & Pitch | /20 | |

### 💼 Strategy & Financial Deconstruction
- **Strategic Thesis:** [Evaluation of candidate's core business approach]
- **Unit Economics Audit:** [CAC, LTV, Margin analysis]
- **Boardroom Pitch Recommendations:** [Actionable pivots for executive approval]"""
}

# ─── Helper: Extract Failed Skills from Report ──────────────────────────────

def _extract_failed_skills_from_report(report_text: str) -> List[str]:
    """
    Parse the LLM-generated report to extract failed/weak skills.
    Looks for patterns like:
      - "Deficits", "Vulnerabilities", "Weak", "Gaps", "Improve"
      - Technical terms mentioned in weakness sections
    """
    failed_skills = []

    # Find the "Deficits" or "Weaknesses" or "Improve" section
    weakness_patterns = [
        r"(?i)(deficit|vulnerabilit|weakness|gap|improve|lacking|weak|critical area|action item).*?(?=#{2,}|\Z)",
    ]

    weakness_sections = []
    for pat in weakness_patterns:
        matches = re.findall(pat, report_text, re.DOTALL)
        weakness_sections.extend(matches)

    # Also extract from the full text — look for skills mentioned with negative context
    from app.services.knapsack_engine import _load_skill_db
    skill_db = _load_skill_db()
    if not skill_db:
        return failed_skills

    report_lower = report_text.lower()
    for skill_name in skill_db:
        pattern = r"\b" + re.escape(skill_name.lower()) + r"\b"
        if re.search(pattern, report_lower):
            # Check if this skill appears near negative context
            for match in re.finditer(pattern, report_lower):
                start = max(0, match.start() - 200)
                end = min(len(report_lower), match.end() + 200)
                context = report_lower[start:end]
                negative_words = ["weak", "gap", "deficit", "improve", "lack", "miss",
                                  "insufficient", "fail", "poor", "below", "struggle",
                                  "needs work", "remediat", "vulnerab", "critical"]
                if any(nw in context for nw in negative_words):
                    if skill_name not in failed_skills:
                        failed_skills.append(skill_name)
                    break

    return failed_skills[:15]  # Cap at 15 to keep knapsack feasible


# ─── Route Handlers ──────────────────────────────────────────────────────────

@router.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Parse a resume PDF or text file and return its raw text content."""
    try:
        content = await file.read()
        if file.filename.lower().endswith(".pdf"):
            from app.services.parser_service import extract_text_from_pdf
            pages = extract_text_from_pdf(content)
            text = "\n".join([p["text"] for p in pages])
            return {"text": text}
        else:
            return {"text": content.decode("utf-8")}
    except Exception as e:
        logger.error(f"[ERROR] Failed to parse resume: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {str(e)}")

@router.post("/test-key")
def test_key(req: TestKeyRequest, current_user: User = Depends(get_current_user)):
    """Test if the client BYOK API key works."""
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API Key is empty.")
    result = test_api_key_sync(req.provider, req.api_key.strip(), req.model)
    if result["status"] == "error":
        raise HTTPException(status_code=401, detail=result["message"])
    return result

@router.post("/init")
def init_coach(req: InitCoachRequest, current_user: User = Depends(get_current_user)):
    from app.services.coach_service import build_batch_question_prompt

    logger.info("STEP 1: init_coach called")

    system_prompt = build_batch_question_prompt(
        req.mode,
        req.role,
        req.level,
        req.num_questions,
        req.jd,
        req.resume
    )

    logger.info("STEP 2: Batching done")

    messages = [
        {"role": "user", "parts": [{"text": "Generate the questions now."}]}
    ]

    logger.info("STEP 3: Sending to LLM")

    result = call_llm_sync(
        req.provider,
        req.api_key.strip(),
        messages,
        req.model,
        system_prompt=system_prompt
    )

    logger.info("STEP 4: LLM response received")

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    raw_content = result["content"]
    cleaned = re.sub(r'```json\s*', '', raw_content)
    cleaned = re.sub(r'```\s*', '', cleaned).strip()
    
    questions = []
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            questions = parsed
        else:
            questions = [str(parsed)]
    except Exception as e:
        logger.error(f"[JSON PARSE ERROR] Could not parse LLM output: {raw_content}")
        questions = [q.strip() for q in raw_content.split('\n') if q.strip() and len(q) > 5][:req.num_questions]
        if not questions:
            questions = [
                "Could you tell me about your background?",
                "What is your most significant technical achievement?",
                "How do you handle conflict in a team?"
            ][:req.num_questions]

    return {
        "status": "success",
        "system_prompt": system_prompt,
        "questions": questions,
        "tokens": result.get("tokens", 0)
    }

@router.post("/batch-evaluate")
def batch_evaluate(req: BatchEvaluateRequest, current_user: User = Depends(get_current_user)):
    """Evaluate batch answers and generate final report."""
    jd_note = "**Job Description:** Tailored & Evaluated" if req.jd else ""
    res_note = "**Resume:** Cross-Examined" if req.resume else ""
    mode_key = req.mode_name.lower().strip()
    mode_rubric = MODE_REPORT_PROMPTS.get(mode_key, MODE_REPORT_PROMPTS["technical"])
    study_hours = req.study_hours or 20
    study_days = req.study_days or 7

    # Construct the QA context
    qa_context = ""
    for i, qa in enumerate(req.qa_pairs):
        qa_context += f"Q{i+1}: {qa.get('question', '')}\nA: {qa.get('answer', '')}\n\n"

    end_prompt = f"""SESSION CONCLUDED. The candidate completed {len(req.qa_pairs)} questions over {req.elapsed}.
Here are the Questions and Answers:
{qa_context}

Provide an exhaustive, brutally honest final performance report strictly calibrated to the {req.level_name} industry bar:

## 🏁 Viva-Verse Final Performance Evaluation

**Arena:** Viva-Verse for {req.mode_name} · **Target Role:** {req.role} ({req.level_name})
**Duration:** {req.elapsed} · **Questions Examined:** {len(req.qa_pairs)}
{jd_note}
{res_note}

### Master Hiring Bar Score: [X]/100

{mode_rubric}

### 🟢 Demonstrated Highlights
- [specific references to strong answers given in this session]

### 🔴 Deficits & Vulnerabilities
- [specific technical or behavioral gaps deconstructed, ALWAYS mention the exact skill names like "Docker", "React", "System Design", etc.]

### 📊 Per-Question Analysis
| Q# | Topic | Score (/10) | Key Strength | Key Weakness | Time Assessment |
|---|---|---|---|---|---|
| Q1 | [topic] | [X]/10 | [strength] | [weakness] | [fast/moderate/slow] |
| Q2 | [topic] | [X]/10 | [strength] | [weakness] | [fast/moderate/slow] |
(continue for all questions)

### Executive Verdict: [HIRE / STRONG LEAN / LEAN NO / DEFINITE NO]

### 💪 Mentor Closing Note
[Inspiring, high-signal closing statement]"""

    system_prompt = build_system_prompt(req.mode_name, req.role, req.level_name, req.jd, req.resume)
    messages = [{"role": "user", "parts": [{"text": end_prompt}]}]
    
    result = call_llm_sync(req.provider, req.api_key.strip(), messages, req.model, system_prompt=system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    report_text = result.get("content", "")

    # Run Knapsack DP
    logger.info(f"STEP 5: Extracting skills from generated report (Length: {len(report_text)} chars)")
    logger.info(f"REPORT PREVIEW: {report_text[:300]}...")
    
    failed_skills = _extract_failed_skills_from_report(report_text)
    remediation_plan = {}
    if failed_skills:
        remediation_plan = knapsack_remediation(
            failed_skills=failed_skills,
            jd_text=req.jd or "",
            total_hours=study_hours,
            num_days=study_days,
        )

        plan_text = f"\n\n### 📅 {study_days}-Day Intensive Remediation Plan (0/1 Knapsack DP Optimized)\n"
        plan_text += f"**Budget:** {study_hours} hours · **Algorithm:** 0/1 Knapsack Dynamic Programming\n\n"

        if remediation_plan.get("selected_skills"):
            plan_text += "| Day | Skill | Study Hours | JD Priority Score |\n"
            plan_text += "|---|---|---|---|\n"
            for skill in remediation_plan["selected_skills"]:
                plan_text += f"| Day {skill['day']} | **{skill['skill']}** | {skill['hours']}h | {skill['priority']} |\n"

            plan_text += f"\n**Total Hours Used:** {remediation_plan['total_hours_used']}/{study_hours}h · "
            plan_text += f"**Total ROI Score:** {remediation_plan['total_roi_score']}\n"

        if remediation_plan.get("dropped_skills"):
            plan_text += "\n**⚠️ Skills Deprioritized by Algorithm (Insufficient Time Budget):**\n"
            for skill in remediation_plan["dropped_skills"]:
                plan_text += f"- ~~{skill['skill']}~~ — {skill['reason']}\n"

        report_text += plan_text

    result["content"] = report_text
    result["remediation_plan"] = remediation_plan
    result["failed_skills"] = failed_skills

    return result

@router.post("/chat")
def chat_coach(req: ChatCoachRequest, current_user: User = Depends(get_current_user)):
    """Execute multi-turn chat interaction."""
    result = call_llm_sync(req.provider, req.api_key.strip(), req.messages, req.model, system_prompt=req.system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.post("/scorecard")
def get_scorecard(req: ScorecardRequest, current_user: User = Depends(get_current_user)):
    """Generate mid-session scorecard."""
    prompt = f"""PAUSE: The candidate requests a mid-session performance review.

Provide a detailed scorecard in this exact format:

## 📊 Mid-Session Scorecard ({req.elapsed} elapsed, {req.question_num} questions)

### Dimension Scores (each out of 10)
1. **Executive Presence** — [score]/10 — [1-line reason]
2. **Technical & Domain Depth** — [score]/10 — [1-line reason]
3. **Structured Problem-Solving** — [score]/10 — [1-line reason]
4. **Communication Precision** — [score]/10 — [1-line reason]
5. **Industry Hiring Bar Alignment** — [score]/10 — [1-line reason]

### 🟢 Top Strengths Demonstrated
- [strength 1]
- [strength 2]

### 🔴 Critical Action Items
- [action 1 — specific + actionable]
- [action 2 — specific + actionable]

### Overall Verdict: [X]/50 — [one-sentence executive assessment]

Be encouraging but brutally honest according to production hiring standards. Then append: 'Let us continue cross-examination. Here is your next question:' and ask the next question."""

    test_msgs = list(req.messages) + [{"role": "user", "parts": [{"text": prompt}]}]
    result = call_llm_sync(req.provider, req.api_key.strip(), test_msgs, req.model, system_prompt=req.system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@router.post("/end-report")
def get_end_report(req: EndReportRequest, current_user: User = Depends(get_current_user)):
    """
    Generate comprehensive final report with DP Knapsack remediation plan.

    Flow:
    1. Ask the LLM for a structured evaluation report.
    2. Parse the report to extract failed skills.
    3. Run the 0/1 Knapsack DP algorithm to generate an optimal study plan.
    4. Inject the mathematically-proven study plan into the report.
    """
    jd_note = "**Job Description:** Tailored & Evaluated" if req.jd else ""
    res_note = "**Resume:** Cross-Examined" if req.resume else ""

    mode_key = req.mode_name.lower().strip()
    mode_rubric = MODE_REPORT_PROMPTS.get(mode_key, MODE_REPORT_PROMPTS["technical"])

    study_hours = req.study_hours or 20
    study_days = req.study_days or 7

    end_prompt = f"""SESSION CONCLUDED. The candidate completed {req.question_num} questions over {req.elapsed}.

Provide an exhaustive, brutally honest final performance report strictly calibrated to the {req.level_name} industry bar:

## 🏁 Viva-Verse Final Performance Evaluation

**Arena:** Viva-Verse for {req.mode_name} · **Target Role:** {req.role} ({req.level_name})
**Duration:** {req.elapsed} · **Questions Examined:** {req.question_num}
{jd_note}
{res_note}

### Master Hiring Bar Score: [X]/100

{mode_rubric}

### 🟢 Demonstrated Highlights
- [specific references to strong answers given in this session]

### 🔴 Deficits & Vulnerabilities
- [specific technical or behavioral gaps deconstructed, ALWAYS mention the exact skill names like "Docker", "React", "System Design", etc.]

### 📊 Per-Question Analysis
| Q# | Topic | Score (/10) | Key Strength | Key Weakness | Time Assessment |
|---|---|---|---|---|---|
| Q1 | [topic] | [X]/10 | [strength] | [weakness] | [fast/moderate/slow] |
| Q2 | [topic] | [X]/10 | [strength] | [weakness] | [fast/moderate/slow] |
(continue for all questions)

### Executive Verdict: [HIRE / STRONG LEAN / LEAN NO / DEFINITE NO]

### 💪 Mentor Closing Note
[Inspiring, high-signal closing statement]"""

    test_msgs = list(req.messages) + [{"role": "user", "parts": [{"text": end_prompt}]}]
    result = call_llm_sync(req.provider, req.api_key.strip(), test_msgs, req.model, system_prompt=req.system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    report_text = result.get("content", "")

    # ── Phase 2: Extract failed skills and run Knapsack DP ──
    failed_skills = _extract_failed_skills_from_report(report_text)
    logger.info(f"[KNAPSACK] Extracted {len(failed_skills)} failed skills: {failed_skills}")

    remediation_plan = {}
    if failed_skills:
        remediation_plan = knapsack_remediation(
            failed_skills=failed_skills,
            jd_text=req.jd or "",
            total_hours=study_hours,
            num_days=study_days,
        )

        # Append the DP-computed remediation plan to the report
        plan_text = f"\n\n### 📅 {study_days}-Day Intensive Remediation Plan (0/1 Knapsack DP Optimized)\n"
        plan_text += f"**Budget:** {study_hours} hours · **Algorithm:** 0/1 Knapsack Dynamic Programming\n\n"

        if remediation_plan.get("selected_skills"):
            plan_text += "| Day | Skill | Study Hours | JD Priority Score |\n"
            plan_text += "|---|---|---|---|\n"
            for skill in remediation_plan["selected_skills"]:
                plan_text += f"| Day {skill['day']} | **{skill['skill']}** | {skill['hours']}h | {skill['priority']} |\n"

            plan_text += f"\n**Total Hours Used:** {remediation_plan['total_hours_used']}/{study_hours}h · "
            plan_text += f"**Total ROI Score:** {remediation_plan['total_roi_score']}\n"

        if remediation_plan.get("dropped_skills"):
            plan_text += "\n**⚠️ Skills Deprioritized by Algorithm (Insufficient Time Budget):**\n"
            for skill in remediation_plan["dropped_skills"]:
                plan_text += f"- ~~{skill['skill']}~~ — {skill['reason']}\n"

        report_text += plan_text

    result["content"] = report_text
    result["remediation_plan"] = remediation_plan
    result["failed_skills"] = failed_skills

    return result

@router.post("/analytics")
def get_analytics(req: AnalyticsRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Parse a completed report into structured analytics JSON for the Dashboard.
    This endpoint extracts scores, strengths, weaknesses, and per-question data
    from the LLM-generated report using regex — no additional API calls needed.
    """
    report = req.report_text

    # ── Extract Master Score ──
    # Broadened to catch "Score: 85", "**Score**: 85/100", "Master Hiring Bar Score: 85"
    score_match = re.search(r"(?:Master\s*Hiring\s*Bar\s*Score|Overall\s*Score|Final\s*Score)[\s:*#]*([0-9]{1,3})(?:\s*/\s*100)?", report, re.IGNORECASE)
    overall_score = int(score_match.group(1)) if score_match else 0

    # ── Extract Competency Matrix Scores ──
    competency_scores = []
    # Make the /20 optional and handle possible markdown bolding around numbers
    dimension_pattern = r"\|\s*([^|]+?)\s*\|\s*\*?(\d+)\*?(?:\s*/\s*20)?\s*\|\s*([^|]+?)\s*\|"
    for match in re.finditer(dimension_pattern, report):
        dim_name = match.group(1).strip()
        dim_score = int(match.group(2))
        dim_critique = match.group(3).strip()
        if dim_name and dim_name != "Evaluation Dimension":
            competency_scores.append({
                "dimension": dim_name,
                "score": dim_score,
                "max_score": 20,
                "critique": dim_critique,
            })

    # ── Extract Per-Question Analysis ──
    per_question = []
    # Make the /10 optional and handle bolding around Q1 or the score
    q_pattern = r"\|\s*\*?Q?(\d+)\*?\s*\|\s*([^|]+?)\s*\|\s*\**(\d+)\**(?:\s*/\s*10)?\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"
    for match in re.finditer(q_pattern, report):
        per_question.append({
            "question_num": int(match.group(1)),
            "topic": match.group(2).strip(),
            "score": int(match.group(3)),
            "max_score": 10,
            "strength": match.group(4).strip(),
            "weakness": match.group(5).strip(),
            "time_assessment": match.group(6).strip(),
        })

    # ── Extract Strengths ──
    strengths = []
    strength_section = re.search(
        r"(?:Demonstrated Highlights|Strengths)(.*?)(?=#{2,}|\Z)", report, re.DOTALL | re.IGNORECASE
    )
    if strength_section:
        for line in strength_section.group(1).split("\n"):
            line = line.strip().lstrip("- •*")
            if line and len(line) > 10 and not line.startswith("|") and not line.startswith("#"):
                strengths.append(line)

    # ── Extract Weaknesses ──
    weaknesses = []
    weakness_section = re.search(
        r"(?:Deficits|Vulnerabilities|Weakness|Gaps)(.*?)(?=#{2,}|\Z)", report, re.DOTALL | re.IGNORECASE
    )
    if weakness_section:
        for line in weakness_section.group(1).split("\n"):
            line = line.strip().lstrip("- •*")
            if line and len(line) > 10 and not line.startswith("|") and not line.startswith("#"):
                weaknesses.append(line)

    # ── Extract Verdict ──
    verdict_match = re.search(r"Executive Verdict:.*?(HIRE|STRONG LEAN|LEAN NO|DEFINITE NO)", report, re.IGNORECASE)
    verdict = verdict_match.group(1).upper() if verdict_match else "PENDING"

    # ── Run Knapsack Remediation ──
    failed_skills = _extract_failed_skills_from_report(report)
    remediation_plan = {}
    if failed_skills:
        remediation_plan = knapsack_remediation(
            failed_skills=failed_skills,
            jd_text=req.jd or "",
            total_hours=req.study_hours or 20,
            num_days=req.study_days or 7,
        )

    # ── JD Skill Priorities (for radar chart) ──
    jd_priorities = extract_skill_priorities(req.jd) if req.jd else {}
    top_jd_skills = sorted(jd_priorities.items(), key=lambda x: x[1], reverse=True)[:10]

    # ── Save to DB ──
    elapsed_secs = 0.0
    if ':' in req.elapsed:
        parts = req.elapsed.split(':')
        elapsed_secs = float(parts[0]) * 60 + float(parts[1])

    new_session = VivaSession(
        user_id=current_user.id,
        mode_name=req.mode_name,
        role=req.role,
        level=req.level_name,
        elapsed_seconds=elapsed_secs,
        question_count=req.question_num,
        overall_score=overall_score,
        answers_json=json.dumps(req.messages) if req.messages else None,
        remediation_json=json.dumps(remediation_plan),
        strengths_json=json.dumps(strengths),
        weaknesses_json=json.dumps(weaknesses)
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    return {
        "session_id": new_session.id,
        "overall_score": overall_score,
        "verdict": verdict,
        "mode": req.mode_name,
        "role": req.role,
        "level": req.level_name,
        "elapsed": req.elapsed,
        "question_count": req.question_num,
        "competency_scores": competency_scores,
        "per_question": per_question,
        "strengths": strengths[:8],
        "weaknesses": weaknesses[:8],
        "remediation_plan": remediation_plan,
        "failed_skills": failed_skills,
        "jd_skill_priorities": [{"skill": s, "priority": round(p, 1)} for s, p in top_jd_skills],
        "report_text": report
    }

@router.get("/sessions")
def get_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(VivaSession).filter(VivaSession.user_id == current_user.id).order_by(VivaSession.created_at.desc()).all()
    return [{
        "id": s.id,
        "mode": s.mode_name,
        "role": s.role,
        "level": s.level,
        "elapsed_seconds": s.elapsed_seconds,
        "question_count": s.question_count,
        "overall_score": s.overall_score,
        "created_at": s.created_at
    } for s in sessions]

@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.query(VivaSession).filter(VivaSession.id == session_id, VivaSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "id": session.id,
        "mode": session.mode_name,
        "role": session.role,
        "level": session.level,
        "elapsed_seconds": session.elapsed_seconds,
        "question_count": session.question_count,
        "overall_score": session.overall_score,
        "created_at": session.created_at,
        "answers": json.loads(session.answers_json) if session.answers_json else None,
        "remediation_plan": json.loads(session.remediation_json) if session.remediation_json else None,
        "strengths": json.loads(session.strengths_json) if session.strengths_json else None,
        "weaknesses": json.loads(session.weaknesses_json) if session.weaknesses_json else None
    }

