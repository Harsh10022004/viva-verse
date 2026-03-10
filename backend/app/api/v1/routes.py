import logging
import uuid
from typing import List, Dict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from fastapi import APIRouter, UploadFile, File, HTTPException
import re
from collections import Counter
from app.utils.constants import STOPWORDS
from app.schemas.models import SubmitAnswerRequest, FinalizeRequest, ConfirmUploadRequest
from app.services.parser_service import DocumentStore, extract_text_from_pdf, chunk_text, generate_questions
from app.services.llm_service import evaluate_answer, SBERTSingleton

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
async def upload_documents(files: List[UploadFile] = File(...)):
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
async def confirm_upload(req: ConfirmUploadRequest):
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
async def start_viva():
    """Generate 6 unique questions and create a new viva session."""
    if len(doc_store.chunks) == 0:
        logger.error("[ERROR 400] Expected chunks but doc_store is empty.")
        raise HTTPException(400, "No documents loaded. Please upload PDFs first.")

    session_id = str(uuid.uuid4())
    questions = generate_questions(doc_store, num=6)

    sessions[session_id] = {
        "questions": questions,
        "answers": {},  # question_id -> {answer, score, critique, source_chunk_index}
    }

    logger.info(f"[SUCCESS] Viva Session {session_id} Started.")
    return {
        "session_id": session_id,
        "questions": [{"id": q["id"], "question": q["question"]} for q in questions],
    }

@router.post("/submit-answer")
async def submit_answer(req: SubmitAnswerRequest):
    """Evaluate a user's answer against the source chunk using cosine similarity."""
    session = sessions.get(req.session_id)
    if not session:
        logger.error(f"[ERROR 404] Session {req.session_id} not found.")
        raise HTTPException(404, "Session not found.")

    question = next((q for q in session["questions"] if q["id"] == req.question_id), None)
    if not question:
        logger.error(f"[ERROR 404] Question {req.question_id} not found.")
        raise HTTPException(404, "Question not found in this session.")

    source_chunk = doc_store.chunks[question["source_chunk_index"]]
    question_text = question["question"]
    q_intent = question.get("intent", "")
    q_topic = question.get("topic", "")
    
    result = evaluate_answer(req.answer, question_text, source_chunk, SBERTSingleton(), intent=q_intent, topic=q_topic)

    session["answers"][req.question_id] = {
        "answer": req.answer,
        "score": result["score"],
        "critique": result["critique"],
        "source_chunk_index": question["source_chunk_index"],
    }

    return {
        "question_id": req.question_id,
        "score": result["score"],
        "critique": result["critique"],
    }

@router.post("/finalize")
async def finalize(req: FinalizeRequest):
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

    answered_map: Dict[int, float] = {a["source_chunk_index"]: a["score"] for a in answers.values()}
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
        {"question": next(q["question"] for q in session["questions"] if q["id"] == qid),
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

    logger.info(f"[SUCCESS] Viva Session {req.session_id} Finalized with Overall Score: {overall_score}.")
    
    return {
        "overall_score": overall_score,
        "topic_mastery": topic_mastery,
        "recall_heatmap": recall_heatmap,
        "areas_for_improvement": areas_text,
        "total_questions": len(session["questions"]),
        "total_answered": len(answers),
        "individual_scores": scores,
    }
