import logging
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PROVIDERS_CONFIG = {
    "google": {
        "name": "Google AI Studio",
        "type": "google",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        "default_model": "gemini-2.5-flash"
    },
    "openrouter": {
        "name": "OpenRouter",
        "type": "openai",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "google/gemma-4-31b-it:free"
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "type": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "default_model": "google/gemma-4-31b-it"
    },
    "huggingface": {
        "name": "Hugging Face",
        "type": "openai",
        "base_url": "https://router.huggingface.co/novita/v3/openai/chat/completions",
        "default_model": "google/gemma-4-31b-it"
    }
}

MODE_PROMPTS = {
    "behavioral": """VIVA-VERSE FOR BEHAVIORAL mode.
- Ask STAR-method behavioral interview questions one at a time.
- After each answer, briefly evaluate: Did they clearly outline Situation, Task, Action, and Result? Were metrics included?
- Probe deeper with intelligent follow-up questions if their response is vague or high-level.
- Core Topics: Leadership, conflict resolution, teamwork, failure recovery, prioritization, executive communication.""",

    "technical": """VIVA-VERSE FOR TECHNICAL mode.
- Ask progressive coding, architectural, and computer science technical questions one at a time.
- If the candidate provides code or pseudocode, evaluate algorithmic correctness, Time/Space Big-O efficiency, and edge cases.
- Ask targeted follow-up optimization questions to test architectural depth.
- Core Topics: Data structures, algorithms, concurrency, system internals, debugging, language-specific nuances.""",

    "system-design": """VIVA-VERSE FOR SYSTEM DESIGN mode.
- Present real-world distributed system design challenges (e.g., Design Distributed Caching, High-Throughput Pub-Sub, Global Video Streaming).
- Guide candidate through structured pillars: Functional Requirements -> Non-Functional Constraints -> High-Level Architecture -> Component Deep Dives -> Fault Tolerance & Tradeoffs.
- Ask clarifying questions if the candidate jumps straight to component selection without establishing scale assumptions.
- Evaluate: Horizontal scalability, partition tolerances, network bottlenecks, database sharding strategies, capacity estimates.""",

    "assessment": """VIVA-VERSE FOR ONLINE ASSESSMENT mode.
- Present timed simulation challenges: quantitative aptitude, advanced logical reasoning, rapid coding brain-teasers.
- Provide crisp problem specifications with exact input/output examples and strict runtime constraints.
- After each response, instantly indicate pass/fail correctness and provide a clean, optimal walkthrough.
- Mix: Complex multiple-choice, short algorithmic snippets, logical deduction puzzles, pattern recognition.""",

    "certification": """VIVA-VERSE FOR CERTIFICATION mode.
- Ask industry certification exam questions (Cloud Architect, Security Specialist, Machine Learning Engineer).
- Provide rigorous multiple-choice and scenario-driven prompts.
- After each candidate choice, explicitly explain WHY the chosen option is correct or incorrect AND deconstruct why every wrong alternative fails.
- Track running performance accuracy and reference canonical documentation architecture frameworks.""",

    "case-study": """VIVA-VERSE FOR CASE STUDY mode.
- Present complex business strategy, product teardown, or market expansion scenarios.
- Guide candidate through methodical structuring: Clarify Objectives -> MECE Framework Decomposition -> Quantitative Financial Analysis -> Strategic Recommendations.
- Evaluate: Structured first-principles thinking, mental math accuracy, executive synthesis, risk mitigation.
- Ask probing stress-test questions regarding customer acquisition costs and margin assumptions."""
}

def build_system_prompt(mode: str, role: str, level: str, jd: Optional[str] = None, resume: Optional[str] = None) -> str:
    mode_instruction = MODE_PROMPTS.get(mode, MODE_PROMPTS["technical"])
    
    context_block = ""
    if jd and jd.strip():
        context_block += f"\n\nTARGET JOB DESCRIPTION (Tailor your interrogation questions strictly to evaluate these specific competencies):\n---\n{jd.strip()}\n---"
    if resume and resume.strip():
        context_block += f"\n\nCANDIDATE RESUME & BACKGROUND (Cross-examine their actual past projects and metrics when providing feedback):\n---\n{resume.strip()}\n---"

    return f"""You are Antigravity Viva-Verse, an elite industry AI Interviewer & Defense Coach powered by Google Gemma 4 architecture. You conduct production-grade, brutally honest interviews calibrated to industry hiring bars.

SESSION METADATA:
- Target Role: {role}
- Experience Bar: {level}
- Active Arena: Viva-Verse for {mode.replace('-', ' ').title()}
{context_block}

{mode_instruction}

PRODUCTION COACHING PROTOCOL:
1. Ask EXACTLY ONE question at a time. Never dump multiple questions. Wait for candidate submission.
2. After candidate response, provide concise, high-signal feedback (2-4 sentences highlighting strengths and concrete flaws), then immediately pose the next question.
3. Strictly calibrate interrogation rigor to the {level} hiring standard.
4. Maintain a classy, executive, industry-grade tone. Do not sugarcoat failures.
5. Format output in rich Markdown: **bold** core takeaways, use structured bullet lists, and enclose code symbols in `backticks`.
6. Prefix question numbers clearly (e.g., **Q1**, **Q2**) for trajectory tracking.
7. If the candidate uploads an architectural sketch or screenshot, perform multi-modal analysis and integrate it directly into the cross-examination.

Begin immediately. Introduce your executive persona in 2 classy sentences and pose **Q1**."""

def test_api_key_sync(provider: str, api_key: str, model: Optional[str] = None) -> Dict[str, Any]:
    """Synchronously ping the provider to verify if the API key is active."""
    cfg = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["google"])
    target_model = model or cfg["default_model"]
    if provider == "google" and target_model.startswith("gemma"):
        target_model = "gemini-2.5-flash"

    try:
        if cfg["type"] == "google":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
            payload = json.dumps({
                "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 5}
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        else:
            url = cfg["base_url"]
            payload = json.dumps({
                "model": target_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }, method="POST")

        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"status": "success", "message": f"Verified BYOK connection to {cfg['name']} ({target_model})"}

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"[BYOK ERROR {e.code}] {provider}: {err_body}")
        return {"status": "error", "message": f"Authentication rejected by {cfg['name']} (HTTP {e.code}). Check API Key."}
    except Exception as e:
        logger.error(f"[BYOK ERROR] Network failure: {str(e)}")
        return {"status": "error", "message": f"Network error connecting to {cfg['name']}: {str(e)}"}

def call_llm_sync(provider: str, api_key: str, messages: List[Dict[str, Any]], model: Optional[str] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Execute multi-turn chat completion using client BYOK credentials."""
    cfg = PROVIDERS_CONFIG.get(provider, PROVIDERS_CONFIG["google"])
    target_model = model or cfg["default_model"]
    if provider == "google" and target_model.startswith("gemma"):
        target_model = "gemini-2.5-flash"

    try:
        if cfg["type"] == "google":
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"
            # Format messages for Gemini REST API
            gemini_contents = []
            for msg in messages:
                role = "model" if msg["role"] in ["assistant", "model", "coach"] else "user"
                parts = []
                for part in msg.get("parts", [{"text": msg.get("content", "")}]):
                    if isinstance(part, dict) and "inlineData" in part:
                        parts.append({"inline_data": part["inlineData"]})
                    elif isinstance(part, dict) and "text" in part:
                        parts.append({"text": part["text"]})
                    elif isinstance(part, str):
                        parts.append({"text": part})
                gemini_contents.append({"role": role, "parts": parts})

            if gemini_contents and gemini_contents[0]["role"] == "model":
                gemini_contents.insert(0, {"role": "user", "parts": [{"text": "Begin interview session."}]})

            req_body = {
                "contents": gemini_contents,
                "generationConfig": {"temperature": 0.75, "maxOutputTokens": 2048, "topP": 0.95}
            }
            if system_prompt and system_prompt.strip():
                req_body["system_instruction"] = {"parts": [{"text": system_prompt.strip()}]}

            payload = json.dumps(req_body).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                c_parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                text = "".join([p.get("text", "") for p in c_parts if not p.get("thought")])
                tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                return {"status": "success", "content": text, "tokens": tokens}

        else:
            url = cfg["base_url"]
            # Format messages for OpenAI Chat Completions REST API
            oai_messages = []
            if system_prompt and system_prompt.strip():
                oai_messages.append({"role": "system", "content": system_prompt.strip()})

            for msg in messages:
                role = "assistant" if msg["role"] in ["assistant", "model", "coach"] else "user"
                content = msg.get("content", "")
                if "parts" in msg:
                    # Check for multimodal image attachments
                    oai_parts = []
                    for p in msg["parts"]:
                        if isinstance(p, dict) and "inlineData" in p:
                            mime = p["inlineData"]["mimeType"]
                            b64 = p["inlineData"]["data"]
                            oai_parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
                        elif isinstance(p, dict) and "text" in p:
                            oai_parts.append({"type": "text", "text": p["text"]})
                    content = oai_parts if len(oai_parts) > 1 else (oai_parts[0]["text"] if oai_parts else "")
                
                oai_messages.append({"role": role, "content": content})

            payload = json.dumps({
                "model": target_model,
                "messages": oai_messages,
                "temperature": 0.75,
                "max_tokens": 2048
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }, method="POST")

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return {"status": "success", "content": text, "tokens": tokens}

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.error(f"[LLM EXECUTION ERROR {e.code}] {provider}: {err_body}")
        return {"status": "error", "message": f"Provider API Error ({e.code}): {err_body[:200]}"}
    except Exception as e:
        logger.error(f"[LLM EXECUTION ERROR]: {str(e)}")
        return {"status": "error", "message": f"Inference failure: {str(e)}"}
