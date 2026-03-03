# Viva-Verse Demonstration Playbook

This playbook outlines **exactly how to trigger** the different scenarios in your defense video to demonstrate Absolute Modularity, Backend Logging Observability, Frontend Toast notifications, and graceful Edge-Case handling.

Before starting:
1. Ensure the Backend is running: `cd backend && python main.py`
2. Ensure the Frontend is running: `cd frontend && npm run dev`
3. Have your terminal (running the backend) clearly visible on one side of the screen, and the frontend on the other.

---

## Scenario 1: The Happy Path (Multi-Doc Upload & Defense)

* **Goal:** Prove the system successfully parses huge PDFs, extracts core semantics, and runs a viva session seamlessly without crashing.
* **How to trigger:** 
  1. Drag and drop 2-3 standard PDF files (like your thesis or project docs) into the Upload dropzone.
  2. Click **"Initialize Space-Bound Engine"**.
  3. Answer a question thoughtfully, hitting `Ctrl+Enter`.
  4. Skip to the end and click **"Next Question →"** until you hit the Dashboard.
* **What to look for on UI:**
  * **Toast:** Green success toast `Documents successfully parsed and engine initialized!` pop-up.
  * **Toast:** `Answer submitted! Score: X%` when answering.
* **What to look for in Terminal:**
  * `[INFO] Parsing Started for a PDF file.`
  * `[INFO] Adding X chunks to DocumentStore.`
  * `[SUCCESS] Total chunks indexed: X`
  * `[SUCCESS] Viva Session X Started.`
  * `[INFO] Execution Started: evaluate_answer`
  * `[SUCCESS] Answer Evaluated with Score: X`

---

## Scenario 2: Edge Case — Unsupported File Format (415)

* **Goal:** Prove that the backend properly validates file inputs at the API layer, catching incorrect extensions before any heavy parsing happens.
* **How to trigger:**
  1. Go to the Upload view.
  2. Click `browse` or drag in a `.txt`, `.docx`, or `.jpg` file.
  3. Click **"Initialize Space-Bound Engine"**.
* **What to look for on UI:**
  * **Toast:** Red error toast `Upload Failed: Only PDF files are accepted. Got: filename.txt`. The system stays stable.
* **What to look for in Terminal:**
  * `[ERROR 415] Unsupported File Format: filename.txt`

---

## Scenario 3: Edge Case — Empty/Nonsense Answers (Graceful Degradation)

* **Goal:** Show what happens when a student submits an empty or useless answer during the viva. The system should not break or give a 500 error, instead scoring it 0.
* **How to trigger:**
  1. During an active Viva session, type only spaces `"   "` or leave it completely blank.
  2. Press **Submit Answer** (or `Ctrl+Enter`).
* **What to look for on UI:**
  * **Toast:** The answer scores `0%`. The critique nicely explains "No answer was provided" or gives a mentor-style failure critique.
* **What to look for in Terminal:**
  * `[WARNING] Empty answer provided.` (If fully empty).
  * Smooth continued execution without stack traces.

---

## Scenario 4: Edge Case — Running Test Suite (Automated CI/CD Proof)

* **Goal:** Fulfill the mentor's requirement for a proper Pytest structure containing happy and edge cases, proving you write professional code.
* **How to trigger:**
  1. In a new terminal tab (inside `backend/`), run the command: `pytest -v tests/`
* **What to look for in Terminal:**
  * Pytest will list the 13 completely automated tests (e.g. `test_upload_valid_pdf`, `test_submit_answer_empty_text`, `test_finalize_no_answers`).
  * All tests should cleanly display **`PASSED`** in green letters, proving absolute reliability.

---

## Scenario 5: Reviewing the Modular Architecture

* **Goal:** Fulfill the absolute modularity requirement visually.
* **How to trigger:**
  1. Open your code editor and show the directory tree file explorer.
* **What to look for:**
  * Point out `app/api/v1/routes.py` (all endpoints separated).
  * Point out `app/services/parser_service.py` and `app/services/llm_service.py` (pure business and AI logic completely separated from endpoints).
  * Point out `app/schemas/models.py` (Pydantic validation layers).
  * Show `tests/test_viva.py` (13 custom tests).
