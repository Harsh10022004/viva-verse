import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.database_models import InterviewQuestion, InterviewRound, InterviewExperience
from sqlalchemy.orm import selectinload
from app.services.vector_store import vector_store
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)

def bm25_search(query: str, db: Session, filters: Dict[str, Any] = None, limit: int = 50) -> Dict[str, float]:
    """Execute lexical search using SQLite FTS5 on experiences."""
    if not query.strip():
        return {}
        
    safe_query = ''.join(e for e in query if e.isalnum() or e.isspace())
    if not safe_query.strip():
        return {}
        
    stop_words = {"a", "an", "the", "and", "or", "but", "if", "then", "else", "when", 
                  "at", "from", "by", "for", "with", "about", "against", "between", 
                  "into", "through", "during", "before", "after", "above", "below", "to", "from", 
                  "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", 
                  "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", 
                  "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", 
                  "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", 
                  "will", "just", "don", "should", "now", "is", "are", "was", "were", "be", 
                  "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing",
                  "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
                  "my", "mine", "your", "yours", "his", "hers", "its", "our", "ours", "their", "theirs",
                  "question", "questions", "interview", "experience", "explain", "tell", "describe", "asked", "what", "how", "who", "which"}
                  
    terms = [term for term in safe_query.lower().split() if term not in stop_words]
    
    if not terms:
        terms = safe_query.lower().split()
        
    fts_match = ' AND '.join(terms)
    
    sql = """
        SELECT e.id, fts.rank 
        FROM interview_experiences_fts fts
        JOIN interview_experiences e ON fts.id = e.id
        WHERE interview_experiences_fts MATCH :match
    """
    
    params = {"match": fts_match}
    
    if filters:
        if filters.get("company"):
            sql += " AND LOWER(e.company) = :company"
            params["company"] = filters["company"].lower()
        if filters.get("role"):
            sql += " AND LOWER(e.role) = :role"
            params["role"] = filters["role"].lower()
        if filters.get("level"):
            sql += " AND LOWER(e.level) = :level"
            params["level"] = filters["level"].lower()
        if filters.get("source") and filters["source"] != "both":
            sql += " AND e.source = :source"
            params["source"] = filters["source"]
        if filters.get("topics"):
            # Simple LIKE for comma-separated topics
            sql += " AND LOWER(e.topics) LIKE :topics"
            params["topics"] = f"%{filters['topics'].lower()}%"
            
    sql += " AND LOWER(e.company) != 'unknown'"
            
    sql += " ORDER BY fts.rank ASC LIMIT :limit"
    params["limit"] = limit
    
    try:
        results = db.execute(text(sql), params).fetchall()
        ranked_results = {}
        for i, row in enumerate(results):
            ranked_results[row[0]] = {"rank": i + 1, "score": float(row[1])}
        return ranked_results
    except Exception as e:
        logger.error(f"FTS5 Search error: {e}")
        return {}

def vector_search(query: str, db: Session, filters: Dict[str, Any] = None, limit: int = 50) -> Dict[str, float]:
    """Execute semantic vector search using FAISS on experiences."""
    if not query.strip():
        return {}
        
    query_vector = generate_embedding(query)
    if not query_vector:
        return {}
        
    # Fetch a large pool to prevent post-filtering starvation (especially for restrictive filters like 'Native')
    fetch_k = vector_store.index.ntotal if vector_store.index else 1000
    faiss_results = vector_store.search(query_vector, top_k=fetch_k)
    
    if not faiss_results:
        return {}
        
    filtered_results = {}
    
    # Extract IDs returned by FAISS
    exp_ids = [exp_id for exp_id, _ in faiss_results]
    
    # To avoid SQLite IN clause limits (usually 999), chunk the IDs
    chunk_size = 900
    valid_exps = set()
    
    for i in range(0, len(exp_ids), chunk_size):
        chunk = exp_ids[i:i + chunk_size]
        e = db.query(InterviewExperience.id).filter(InterviewExperience.id.in_(chunk))
        
        if filters:
            if filters.get("company"):
                e = e.filter(InterviewExperience.company.ilike(filters["company"]))
            if filters.get("role"):
                e = e.filter(InterviewExperience.role.ilike(filters["role"]))
            if filters.get("level"):
                e = e.filter(InterviewExperience.level.ilike(filters["level"]))
            if filters.get("source") and filters["source"] != "both":
                e = e.filter(InterviewExperience.source == filters["source"])
            if filters.get("topics"):
                e = e.filter(InterviewExperience.topics.ilike(f"%{filters['topics']}%"))
                
        e = e.filter(InterviewExperience.company.notilike('unknown'))
        
        valid_exps.update([exp.id for exp in e.all()])
    
    rank = 1
    for exp_id, score in faiss_results:
        if exp_id in valid_exps:
            filtered_results[exp_id] = {"rank": rank, "score": float(score)}
            rank += 1
            if rank > limit:
                break
                
    return filtered_results

def hybrid_search(query: str, filters: Dict[str, Any] = None, page: int = 1, page_size: int = 20, k: int = 60, top_k: Optional[int] = None) -> Dict[str, Any]:
    """Execute hybrid search on experiences combining BM25 and Vector Search using RRF."""
    db = SessionLocal()
    try:
        if top_k is not None:
            limit = top_k
            page = 1
            page_size = top_k
        else:
            limit = max(page * page_size, 100)
            
        bm25_ranks = bm25_search(query, db, filters, limit=limit)
        vector_ranks = vector_search(query, db, filters, limit=limit)
        
        rrf_scores = {}
        all_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        for exp_id in all_ids:
            score = 0.0
            if exp_id in bm25_ranks:
                score += 1.0 / (k + bm25_ranks[exp_id]["rank"])
            if exp_id in vector_ranks:
                score += 3.0 / (k + vector_ranks[exp_id]["rank"])
            rrf_scores[exp_id] = score
            
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_ids = [exp_id for exp_id, _ in sorted_results[start_idx:end_idx]]
        
        experiences_data = []
        if paginated_ids:
            cases = {exp_id: i for i, exp_id in enumerate(paginated_ids)}
            
            db_exps = db.query(InterviewExperience).options(
                selectinload(InterviewExperience.rounds).selectinload(InterviewRound.questions)
            ).filter(InterviewExperience.id.in_(paginated_ids)).all()
            db_exps.sort(key=lambda x: cases[x.id])
            
            for e in db_exps:
                # Build a snippet of questions
                questions_snippet = []
                for r in e.rounds:
                    for q in r.questions:
                        questions_snippet.append(q.question_text)
                
                if questions_snippet:
                    snippet = " | ".join(questions_snippet)[:150] + ("..." if len(" | ".join(questions_snippet)) > 150 else "")
                elif e.overall_experience:
                    snippet = e.overall_experience[:150] + ("..." if len(e.overall_experience) > 150 else "")
                else:
                    snippet = ""
                
                experiences_data.append({
                    "id": e.id,
                    "company": e.company,
                    "role": e.role,
                    "level": e.level,
                    "topics": e.topics,
                    "source": e.source,
                    "snippet": snippet,
                    "overall_experience": e.overall_experience,
                    "rrf_score": rrf_scores[e.id],
                    "bm25_rank": bm25_ranks[e.id]["rank"] if e.id in bm25_ranks else None,
                    "bm25_score": bm25_ranks[e.id]["score"] if e.id in bm25_ranks else None,
                    "vector_rank": vector_ranks[e.id]["rank"] if e.id in vector_ranks else None,
                    "vector_score": vector_ranks[e.id]["score"] if e.id in vector_ranks else None
                })
                
        return {
            "total": len(sorted_results),
            "page": page,
            "page_size": page_size,
            "results": experiences_data
        }
    finally:
        db.close()

import statistics
import json
from app.database_models import SearchSubscription
from app.services.notification_service import send_email_alert, send_whatsapp_alert
import numpy as np

def calculate_subscription_threshold(query_vector: List[float], top_k: int = 10) -> float:
    """
    Calculate the threshold for a subscription.
    Instead of standard deviation, we use a fixed empirical threshold of 0.95.
    For all-MiniLM-L6-v2, L2 distances < 0.95 represent highly relevant semantic matches.
    """
    return 0.95

def check_subscriptions_for_new_post(exp_id: str, query_text_for_log: str = ""):
    """Background task to check if a new post matches any active subscriptions."""
    db = SessionLocal()
    try:
        new_exp = db.query(InterviewExperience).filter(InterviewExperience.id == exp_id).first()
        if not new_exp or not new_exp.embedding:
            return
            
        new_vector = np.array(json.loads(new_exp.embedding), dtype=np.float32).reshape(1, -1)
        
        subscriptions = db.query(SearchSubscription).all()
        for sub in subscriptions:
            if not sub.query_embedding:
                continue
                
            sub_vector = np.array(json.loads(sub.query_embedding), dtype=np.float32).reshape(1, -1)
            
            # Calculate L2 distance between new post and subscription query
            # (matches FAISS IndexFlatL2 logic)
            distance = float(np.sum((new_vector - sub_vector) ** 2))
            
            # If distance is less than or equal to threshold, it's a match!
            if distance <= sub.threshold_score:
                logger.info(f"MATCH FOUND: Experience {exp_id} matched subscription for '{sub.query_text}'. Score: {distance:.4f} <= Threshold: {sub.threshold_score:.4f}")
                if sub.contact_email:
                    send_email_alert(sub.contact_email, sub.query_text, exp_id)
                if sub.contact_whatsapp:
                    send_whatsapp_alert(sub.contact_whatsapp, sub.query_text, exp_id)
                    
    except Exception as e:
        logger.error(f"Error checking subscriptions: {e}")
    finally:
        db.close()
