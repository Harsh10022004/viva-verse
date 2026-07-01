from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import logging
from app.utils.auth import get_current_user
from app.database_models import User
from app.services.coach_service import test_api_key_sync, call_llm_sync, build_system_prompt

logger = logging.getLogger(__name__)
router = APIRouter()

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
    """Initialize a coaching session and generate the opening question."""
    system_prompt = build_system_prompt(req.mode, req.role, req.level, req.jd, req.resume)
    messages = [{"role": "user", "parts": [{"text": system_prompt}]}]
    
    result = call_llm_sync(req.provider, req.api_key.strip(), messages, req.model, system_prompt=system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
        
    return {
        "status": "success",
        "system_prompt": system_prompt,
        "initial_message": result["content"],
        "tokens": result.get("tokens", 0)
    }

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
    """Generate comprehensive final report."""
    jd_note = "**Job Description:** Tailored & Evaluated" if req.jd else ""
    res_note = "**Resume:** Cross-Examined" if req.resume else ""

    mode_key = req.mode_name.lower().strip()
    mode_rubric = MODE_REPORT_PROMPTS.get(mode_key, MODE_REPORT_PROMPTS["technical"])

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
- [specific technical or behavioral gaps deconstructed]

### 📅 7-Day Intensive Remediation Plan
1. **Day 1-2:** [concrete technical deep dive]
2. **Day 3-4:** [concrete architectural or mock exercise]
3. **Day 5-7:** [final calibration review]

### Executive Verdict: [HIRE / STRONG LEAN / LEAN NO / DEFINITE NO]

### 💪 Mentor Closing Note
[Inspiring, high-signal closing statement]"""

    test_msgs = list(req.messages) + [{"role": "user", "parts": [{"text": end_prompt}]}]
    result = call_llm_sync(req.provider, req.api_key.strip(), test_msgs, req.model, system_prompt=req.system_prompt)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result
