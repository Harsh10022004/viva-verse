import logging
import uuid
from typing import List, Dict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter, UploadFile, File, HTTPException
import re
from collections import Counter
from app.utils.constants import STOPWORDS
from app.schemas.models import SubmitAnswerRequest, FinalizeRequest, ConfirmUploadRequest, StartVivaRequest
from app.services.parser_service import DocumentStore, extract_text_from_pdf, chunk_text, generate_questions
from app.services.llm_service import evaluate_answer, SBERTSingleton
from app.services.agent_orchestrator import SupervisorAgent
from fastapi import Depends
from app.utils.auth import get_current_user
from app.database_models import User, VivaSession
from app.database import get_db
from sqlalchemy.orm import Session
import json

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory stores
sessions: Dict[str, Dict] = {}
pending_uploads: Dict[str, Dict] = {}
doc_store = DocumentStore()

def extract_top_keywords(text: str, top_n=8) -> set:
    words = re.findall(r'[A-Za-z]+', text.lower())
    valid_words = [w for w in words if w not in STOPWORDS and len(w) > 4]
    return set([w for w, c in Counter(valid_words).most_common(top_n)])

@router.post("/upload")
async def upload_documents(files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)):
    """Parse multiple PDFs into semantic text chunks and load into the engine."""
    global doc_store
    doc_store = DocumentStore()  # reset on new upload
    upload_id = str(uuid.uuid4())

    file_chunks: Dict[str, List[str]] = {}
    file_labels: Dict[str, List[str]] = {}
    seen_filenames = set()
    sbert_model = SBERTSingleton()
    document_summaries: Dict[str, str] = {}
    document_keywords: Dict[str, set] = {}

    logger.info(f"[INFO] Upload endpoint hit. Processing {len(files)} file(s).")
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            logger.error(f"[ERROR 415] Unsupported File Format: {f.filename}")
            raise HTTPException(415, f"Only PDF files are accepted. Got: {f.filename}")
        
        if f.filename in seen_filenames:
            logger.warning(f"[WARNING] Duplicate file detected: {f.filename}")
            raise HTTPException(400, f"Duplicate file detected: {f.filename}")
        seen_filenames.add(f.filename)

        try:
            content = await f.read()
            
            import os
            os.makedirs("temp_uploads", exist_ok=True)
            pdf_path = os.path.join("temp_uploads", f"{upload_id}_{f.filename}")
            with open(pdf_path, "wb") as pdf_file:
                pdf_file.write(content)
            doc_store.pdf_paths[f.filename] = pdf_path

            pages = extract_text_from_pdf(content)
            chunks, labels = chunk_text(pages)
            
            if not chunks:
                logger.error(f"[ERROR 400] Blank or image-only PDF: {f.filename}")
                raise HTTPException(400, f"The file '{f.filename}' contains no readable text or is entirely comprised of images.")
                
            labels = [f"{f.filename} — {lbl}" for lbl in labels]
            file_chunks[f.filename] = chunks
            file_labels[f.filename] = labels

            # Store summary and top frequent keywords
            summary_text = " ".join(chunks[:3])[:2500] 
            document_summaries[f.filename] = summary_text
            document_keywords[f.filename] = extract_top_keywords(" ".join(chunks))

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[ERROR 500] Error processing {f.filename}: {str(e)}")
            raise HTTPException(500, f"Failed to process {f.filename}.")

    filenames = list(file_chunks.keys())
    if not filenames:
        logger.error("[ERROR 400] No readable text found in PDFs.")
        raise HTTPException(400, "No readable text found in the uploaded PDFs.")

    warnings = []
    conflicts = []

    # Cross-document semantic similarity check for conflicts
    if len(filenames) > 1:
        logger.info("[INFO] Performing semantic contradiction check across documents.")
        
        # 1. Unrelated Topics Warning
        summaries = [document_summaries[fn] for fn in filenames]
        embeddings = sbert_model.encode(summaries)
        
        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                if sim < 0.20:
                    warnings.append(f"Uploaded documents '{filenames[i]}' and '{filenames[j]}' seem to be from completely different topics.")
        
        # 2. Factual Contradiction Detection
        for i in range(len(filenames)):
            for j in range(i + 1, len(filenames)):
                fn_i = filenames[i]
                fn_j = filenames[j]
                
                shared_topics = document_keywords[fn_i].intersection(document_keywords[fn_j])
                for topic in shared_topics:
                    chunks_i = [c for c in file_chunks[fn_i] if topic in c.lower()]
                    chunks_j = [c for c in file_chunks[fn_j] if topic in c.lower()]
                    
                    if not chunks_i or not chunks_j:
                        continue
                    
                    emb_i = sbert_model.encode(chunks_i)
                    emb_j = sbert_model.encode(chunks_j)
                    
                    sim_matrix = cosine_similarity(emb_i, emb_j)
                    max_sim = np.max(sim_matrix)
                    
                    # Heuristic: if max similarity is moderate, it's a semantic contradiction!
                    # < 0.30 is orthogonal facts. > 0.65 is agreement.
                    if 0.30 <= max_sim <= 0.65:
                        conflicts.append({
                            "topic": topic.capitalize(),
                            "conflicting_docs": [fn_i, fn_j]
                        })

    # De-duplicate conflicts
    unique_conflicts = []
    seen_conflicts = set()
    for c in conflicts:
        key = (c["topic"], tuple(sorted(c["conflicting_docs"])))
        if key not in seen_conflicts:
            seen_conflicts.add(key)
            unique_conflicts.append(c)

    if unique_conflicts or warnings:
        logger.warning(f"[WARNING] Upload requires confirmation. Conflicts: {len(unique_conflicts)}")
        pending_uploads[upload_id] = {
            "file_chunks": file_chunks,
            "file_labels": file_labels
        }
        return {
            "status": "requires_confirmation",
            "upload_id": upload_id,
            "warnings": list(set(warnings)),
            "conflicts": unique_conflicts
        }

    # Clean upload
    all_chunks = []
    all_labels = []
    for fn in filenames:
        all_chunks.extend(file_chunks[fn])
        all_labels.extend(file_labels[fn])

    doc_store.add_chunks(all_chunks, all_labels)
    logger.info(f"[SUCCESS] Total chunks indexed: {len(doc_store.chunks)}")

    return {
        "status": "success",
        "total_chunks": len(doc_store.chunks),
        "message": f"Space-Bound Engine initialized with {len(doc_store.chunks)} semantic chunks.",
    }

@router.post("/confirm-upload")
async def confirm_upload(req: ConfirmUploadRequest, current_user: User = Depends(get_current_user)):
    """Resolve conflicts with user priority and finalize document upload."""
    if req.upload_id not in pending_uploads:
        raise HTTPException(404, "Upload session not found or expired.")
        
    data = pending_uploads[req.upload_id]
    file_chunks = data["file_chunks"]
    file_labels = data["file_labels"]
    
    # Apply priority logic
    for topic, docs_priority in req.priorities.items():
        if len(docs_priority) < 2:
            continue
            
        loser_docs = docs_priority[1:]
        topic_lower = topic.lower()
        
        # Discard conflicting facts from lower priority documents
        for doc in loser_docs:
            if doc in file_chunks:
                filtered_chunks = []
                filtered_labels = []
                for c, l in zip(file_chunks[doc], file_labels[doc]):
                    if topic_lower not in c.lower():
                        filtered_chunks.append(c)
                        filtered_labels.append(l)
                file_chunks[doc] = filtered_chunks
                file_labels[doc] = filtered_labels
                
    # Flatten everything
    all_chunks = []
    all_labels = []
    for fn, chunks in file_chunks.items():
        all_chunks.extend(chunks)
        all_labels.extend(file_labels[fn])
        
    global doc_store
    doc_store.add_chunks(all_chunks, all_labels)
    del pending_uploads[req.upload_id]
    
    logger.info(f"[SUCCESS] Conflicts resolved. Engine loaded with {len(doc_store.chunks)} chunks.")
    return {
        "status": "success",
        "total_chunks": len(doc_store.chunks),
        "message": f"Conflicts resolved! Space-Bound Engine initialized with {len(doc_store.chunks)} chunks."
    }

@router.post("/start-viva")
async def start_viva(req: StartVivaRequest = StartVivaRequest(mode="quick"), current_user: User = Depends(get_current_user)):
    """Start a new viva session. Mode determines static vs agent-driven flow."""
    if len(doc_store.chunks) == 0:
        logger.error("[ERROR 400] Expected chunks but doc_store is empty.")
        raise HTTPException(400, "No documents loaded. Please upload PDFs first.")

    session_id = str(uuid.uuid4())
    num_questions = req.num_questions if hasattr(req, 'num_questions') and req.num_questions else 6
    
    if req.mode == "comprehensive":
        supervisor = SupervisorAgent(doc_store, max_questions=num_questions)
        action = supervisor.get_next_action()
        questions = [action["question"]]
        
        sessions[session_id] = {
            "mode": "comprehensive",
            "supervisor": supervisor,
            "current_question": action["question"],
            "questions": questions, # keep for compat
            "answers": {},
        }
        logger.info(f"[SUCCESS] Comprehensive Viva Session {session_id} Started.")
        return {
            "session_id": session_id,
            "mode": "comprehensive",
            "questions": [{"id": q["id"], "question": q["question"], "context_label": q.get("context_label", "")} for q in questions],
        }
    else:
        questions = generate_questions(doc_store, num=num_questions)
        sessions[session_id] = {
            "mode": "quick",
            "questions": questions,
            "answers": {},  
        }
        logger.info(f"[SUCCESS] Quick Viva Session {session_id} Started.")
        return {
            "session_id": session_id,
            "mode": "quick",
            "questions": [{"id": q["id"], "question": q["question"], "context_label": q.get("context_label", "")} for q in questions],
        }

@router.post("/submit-answer")
async def submit_answer(req: SubmitAnswerRequest, current_user: User = Depends(get_current_user)):
    """Evaluate a user's answer. In comprehensive mode, return the next dynamic question."""
    session = sessions.get(req.session_id)
    if not session:
        logger.error(f"[ERROR 404] Session {req.session_id} not found.")
        raise HTTPException(404, "Session not found.")

    if session.get("mode") == "comprehensive":
        supervisor: SupervisorAgent = session["supervisor"]
        question = session["current_question"]
        
        if question["id"] != req.question_id:
            raise HTTPException(400, "Question ID mismatch.")
            
        result = supervisor.process_answer(req.answer, question)
        
        # Save for finalize compat
        session["answers"][req.question_id] = {
            "answer": req.answer,
            "score": result["score"],
            "critique": result["critique"],
            "source_chunk_index": question["source_chunk_index"],
        }
        
        next_action = supervisor.get_next_action()
        
        if next_action["action"] == "complete":
            # Just store the map so finalize can access it if needed, or return directly
            session["knowledge_map"] = next_action["knowledge_map"]
            return {
                "question_id": req.question_id,
                "score": result["score"],
                "critique": result["critique"],
                "is_complete": True
            }
        else:
            new_question = next_action["question"]
            session["current_question"] = new_question
            session["questions"].append(new_question)
            return {
                "question_id": req.question_id,
                "score": result["score"],
                "critique": result["critique"],
                "is_complete": False,
                "next_question": {
                    "id": new_question["id"], 
                    "question": new_question["question"], 
                    "context_label": new_question.get("context_label", "")
                }
            }
            
    else:
        # Quick Mode Legacy Logic
        question = next((q for q in session["questions"] if q["id"] == req.question_id), None)
        if not question:
            logger.error(f"[ERROR 404] Question {req.question_id} not found.")
            raise HTTPException(404, "Question not found in this session.")

        source_chunk = question.get("cluster_text", doc_store.chunks[question["source_chunk_index"]])
        question_text = question["question"]
        q_intent = question.get("intent", "")
        q_topic = question.get("topic", "")
        
        result = evaluate_answer(req.answer, question_text, source_chunk, SBERTSingleton(), intent=q_intent, topic=q_topic)

        session["answers"][req.question_id] = {
            "answer": req.answer,
            "score": result["score"],
            "critique": result["critique"],
            "source_chunk_index": question["source_chunk_index"],
            "cluster_indices": question.get("cluster_indices", [question["source_chunk_index"]]),
        }

        return {
            "question_id": req.question_id,
            "score": result["score"],
            "critique": result["critique"],
            "is_complete": len(session["answers"]) == len(session["questions"])
        }

@router.post("/finalize")
async def finalize(req: FinalizeRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Aggregate scores and return full analytics for the dashboard."""
    session = sessions.get(req.session_id)
    if not session:
        logger.error(f"[ERROR 404] Session {req.session_id} not found.")
        raise HTTPException(404, "Session not found.")

    answers = session["answers"]
    if not answers:
        logger.error("[ERROR 400] Finalize called but no answers provided.")
        raise HTTPException(400, "No answers submitted yet.")

    scores = [a["score"] for a in answers.values()]
    overall_score = round(sum(scores) / len(scores), 1)

    label_scores: Dict[str, List[float]] = {}
    for a in answers.values():
        label = doc_store.chunk_labels[a["source_chunk_index"]]
        short_label = label.split("—")[-1].strip() if "—" in label else label
        label_scores.setdefault(short_label, []).append(a["score"])

    topic_mastery = [
        {"topic": label, "score": round(sum(s) / len(s), 1)}
        for label, s in label_scores.items()
    ]

    while len(topic_mastery) < 3:
        topic_mastery.append({"topic": f"Section {len(topic_mastery)+1}", "score": 0})

    # Propagate the semantic cluster score to ALL chunks within that cluster!
    answered_map: Dict[int, float] = {}
    for a in answers.values():
        cluster_indices = a.get("cluster_indices", [a["source_chunk_index"]])
        for idx in cluster_indices:
            answered_map[idx] = a["score"]

    recall_heatmap = []
    for i, chunk in enumerate(doc_store.chunks):
        score = answered_map.get(i, -1)
        if score >= 70:
            color = "#22c55e"
        elif score >= 40:
            color = "#eab308"
        elif score >= 0:
            color = "#ef4444"
        else:
            color = "#374151"
        recall_heatmap.append({
            "section": doc_store.chunk_labels[i],
            "chunk_index": i,
            "score": score,
            "color": color,
        })

    weak = [
        {"question": next((q["question"] for q in session["questions"] if q["id"] == qid), "Unknown question"),
         "score": a["score"],
         "critique": a["critique"]}
        for qid, a in answers.items() if a["score"] < 60
    ]
    if weak:
        areas_text = "Focus on the following areas:\n" + "\n".join(
            f"• (Score: {w['score']}%) {w['critique']}" for w in weak
        )
    else:
        areas_text = "Great job! You demonstrated strong understanding across all tested areas."

    # Build grouped knowledge map for Dashboard.jsx
    # Dashboard expects: [ { file_name: str, chunks: [ { text: str, score: float | -1 } ] } ]
    grouped_map = {}
    
    # If comprehensive mode, we might have inferred scores from the agent
    agent_scores = []
    if session.get("mode") == "comprehensive":
        agent_map = session.get("knowledge_map", [])
        # agent_map is a flat list: [{"index": i, "score": s, ...}]
        agent_scores = [item.get("score") for item in agent_map]
    
    for i, chunk_text in enumerate(doc_store.chunks):
        label = doc_store.chunk_labels[i]
        file_name = label.split(" — ")[0] if " — " in label else label
        
        # Determine score
        score = -1 # default untested
        if session.get("mode") == "comprehensive" and agent_scores and i < len(agent_scores):
            # Use agent's inferred score if available
            s = agent_scores[i]
            if s is not None:
                score = s
        else:
            # Quick mode: fully shaded!
            if i in answered_map:
                score = answered_map[i]
                
        if file_name not in grouped_map:
            grouped_map[file_name] = []
            
        grouped_map[file_name].append({
            "text": chunk_text,
            "score": score
        })
        
    final_knowledge_map = [
        {"file_name": fn, "chunks": chunks} 
        for fn, chunks in grouped_map.items()
    ]

    session["final_knowledge_map"] = final_knowledge_map
    
    # Save session to DB
    try:
        db_session = VivaSession(
            id=req.session_id,
            user_id=current_user.id,
            mode=session.get("mode", "quick"),
            overall_score=overall_score,
            answers_json=json.dumps(answers),
            heatmap_json=json.dumps(recall_heatmap),
            knowledge_map_json=json.dumps(final_knowledge_map)
        )
        db.add(db_session)
        db.commit()
    except Exception as e:
        logger.error(f"[ERROR] Failed to save session to DB: {str(e)}")
        db.rollback()
    
    logger.info(f"[SUCCESS] Viva Session {req.session_id} Finalized with Overall Score: {overall_score}.")
    
    return {
        "session_id": req.session_id,
        "mode": session.get("mode", "quick"),
        "overall_score": overall_score,
        "topic_mastery": topic_mastery,
        "recall_heatmap": recall_heatmap,
        "areas_for_improvement": areas_text,
        "total_questions": len(session["questions"]),
        "total_answered": len(answers),
        "individual_scores": scores,
        "knowledge_map": final_knowledge_map
    }

from fastapi.responses import FileResponse
import os
import fitz

@router.get("/download-report/{session_id}")
async def download_report(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate and return an annotated PDF with performance highlights."""
    session = sessions.get(session_id)
    
    # If not in memory, try to load from DB
    if not session or "final_knowledge_map" not in session:
        db_session = db.query(VivaSession).filter(VivaSession.id == session_id, VivaSession.user_id == current_user.id).first()
        if db_session and db_session.knowledge_map_json:
            session = {
                "final_knowledge_map": json.loads(db_session.knowledge_map_json)
            }
            
    if not session or "final_knowledge_map" not in session:
        raise HTTPException(404, "Session not found or not finalized.")

    final_knowledge_map = session["final_knowledge_map"]
    
    # We will generate a single combined PDF if there are multiple documents, or just one.
    # For simplicity, we annotate the first document uploaded.
    # In a full implementation we'd merge them, but here we'll return the first one.
    if not final_knowledge_map:
        raise HTTPException(400, "No documents mapped.")
        
    doc_info = final_knowledge_map[0]
    file_name = doc_info["file_name"]
    
    # Try direct lookup first, then fuzzy match (handles edge cases)
    pdf_path = doc_store.pdf_paths.get(file_name)
    if not pdf_path:
        # Try matching by basename in case the key is stored differently
        for key, path in doc_store.pdf_paths.items():
            if key.endswith(file_name) or file_name.endswith(key):
                pdf_path = path
                file_name = key
                break

    if not pdf_path:
        logger.error(f"[ERROR] PDF not found. file_name={file_name}, known keys={list(doc_store.pdf_paths.keys())}")
        raise HTTPException(404, f"Original PDF not found on server. Known files: {list(doc_store.pdf_paths.keys())}")

    if not os.path.exists(pdf_path):
        raise HTTPException(404, f"PDF file was deleted from disk: {pdf_path}")
        
    out_pdf_path = os.path.join("temp_uploads", f"annotated_{session_id}_{file_name}")
    
    try:
        pdf_document = fitz.open(pdf_path)
        
        # Insert Legend Page at the beginning
        legend_page = pdf_document.new_page(pno=0, width=595, height=842)
        
        # Draw background header
        legend_page.draw_rect(fitz.Rect(0, 0, 595, 120), color=(0.1, 0.1, 0.15), fill=(0.1, 0.1, 0.15))
        legend_page.insert_text((50, 70), "Viva Verse: Semantic Mastery Report", fontsize=24, color=(1, 1, 1), fontname="hebo")
        
        # Draw introductory text
        legend_page.insert_text((50, 160), "This document has been AI-annotated based on your Viva performance.", fontsize=12, fontname="helv")
        legend_page.insert_text((50, 180), "Highlights indicate semantic chunks tested during the session.", fontsize=12, fontname="helv")
        
        # Draw Legend entries (distinct colors)
        legend_page.insert_text((50, 240), "Understanding Levels:", fontsize=16, fontname="hebo")
        
        # Green (Strong)
        legend_page.draw_rect(fitz.Rect(50, 270, 80, 300), color=(0.3, 0.8, 0.5), fill=(0.52, 0.93, 0.67))
        legend_page.insert_text((100, 290), "Strong Mastery (Score >= 75%)", fontsize=14, fontname="helv")
        
        # Yellow (Fair)
        legend_page.draw_rect(fitz.Rect(50, 320, 80, 350), color=(0.9, 0.7, 0.1), fill=(0.99, 0.88, 0.27))
        legend_page.insert_text((100, 340), "Fair/Partial Understanding (Score 45% - 74%)", fontsize=14, fontname="helv")
        
        # Red (Weak)
        legend_page.draw_rect(fitz.Rect(50, 370, 80, 400), color=(0.8, 0.3, 0.3), fill=(0.98, 0.65, 0.65))
        legend_page.insert_text((100, 390), "Weak/Critical Gap (Score < 45%)", fontsize=14, fontname="helv")
        
        # Note about missing chunks
        legend_page.insert_text((50, 450), "* Unhighlighted text means that section was not tested or was filtered out.", fontsize=10, fontname="helv")

        for chunk in doc_info["chunks"]:
            score = chunk["score"]
            text = chunk["text"]
            if score < 0:
                continue # Untested
            
            # Colors in fitz are RGB from 0 to 1
            if score >= 75:
                color = (0.52, 0.93, 0.67) # Green
            elif score >= 45:
                color = (0.99, 0.88, 0.27) # Yellow
            else:
                color = (0.98, 0.65, 0.65) # Red
                
            # Break chunk into 5-word phrases and search for each to highlight the entire chunk
            words = text.split()
            phrases = []
            for i in range(0, len(words), 5):
                phrase = " ".join(words[i:i+5])
                if len(phrase.strip()) > 3:
                    phrases.append(phrase)
            
            # Start from page 1 since page 0 is our legend
            for page_idx in range(1, len(pdf_document)):
                page = pdf_document[page_idx]
                for phrase in phrases:
                    text_instances = page.search_for(phrase)
                    for inst in text_instances:
                        annot = page.add_highlight_annot(inst)
                        annot.set_colors(stroke=color)
                        annot.update()
                    
        pdf_document.save(out_pdf_path)
        pdf_document.close()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"[ERROR] Failed to generate annotated PDF: {e}\n{tb}")
        raise HTTPException(500, f"Failed to generate report: {type(e).__name__}: {str(e)}")
        
    return FileResponse(out_pdf_path, filename=f"Viva_Report_{file_name}", media_type="application/pdf")

@router.get("/sessions")
async def get_user_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all past sessions for the current user."""
    db_sessions = db.query(VivaSession).filter(VivaSession.user_id == current_user.id).order_by(VivaSession.created_at.desc()).all()
    return [
        {
            "id": s.id,
            "mode": s.mode,
            "overall_score": s.overall_score,
            "created_at": s.created_at.isoformat(),
        }
        for s in db_sessions
    ]

@router.get("/sessions/{session_id}")
async def get_session_details(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get details of a specific past session."""
    s = db.query(VivaSession).filter(VivaSession.id == session_id, VivaSession.user_id == current_user.id).first()
    if not s:
        raise HTTPException(404, "Session not found")
        
    return {
        "id": s.id,
        "mode": s.mode,
        "overall_score": s.overall_score,
        "created_at": s.created_at.isoformat(),
        "answers": json.loads(s.answers_json) if s.answers_json else {},
        "recall_heatmap": json.loads(s.heatmap_json) if s.heatmap_json else [],
        "knowledge_map": json.loads(s.knowledge_map_json) if s.knowledge_map_json else []
    }
