import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal
from app.database_models import InterviewQuestion, InterviewRound, InterviewExperience
from app.services.vector_store import vector_store
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)

def bm25_search(query: str, db: Session, filters: Dict[str, Any] = None, limit: int = 50) -> Dict[str, float]:
    """Execute lexical search using SQLite FTS5."""
    if not query.strip():
        return {}
        
    # SQLite FTS5 query format: MATCH 'query'
    # Sanitize query by removing quotes and special characters
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
                  "my", "mine", "your", "yours", "his", "hers", "its", "our", "ours", "their", "theirs"}
                  
    terms = [term for term in safe_query.lower().split() if term not in stop_words]
    
    if not terms:
        # Fallback if the query ONLY contains stop words
        terms = safe_query.lower().split()
        
    fts_match = ' OR '.join(terms) # simple OR for meaningful terms
    
    # Base query joining FTS with metadata tables
    sql = """
        SELECT q.id, fts.rank 
        FROM interview_questions_fts fts
        JOIN interview_questions q ON fts.id = q.id
        JOIN interview_rounds r ON q.round_id = r.id
        JOIN interview_experiences e ON r.experience_id = e.id
        WHERE interview_questions_fts MATCH :match
    """
    
    params = {"match": fts_match}
    
    # Add filters
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
            
    sql += " ORDER BY fts.rank ASC LIMIT :limit" # SQLite rank is lower=better
    params["limit"] = limit
    
    try:
        results = db.execute(text(sql), params).fetchall()
        
        # SQLite rank is usually a negative number or a positive cost, lower is better.
        # We need to assign a score where higher is better for RRF, but actually RRF just needs a rank (1, 2, 3...)
        # We return a dict of {id: rank_position}
        ranked_results = {}
        for i, row in enumerate(results):
            # SQLite FTS5 rank is often negative, where more negative is a stronger match.
            # We'll expose it directly.
            ranked_results[row[0]] = {"rank": i + 1, "score": float(row[1])}
            
        return ranked_results
    except Exception as e:
        logger.error(f"FTS5 Search error: {e}")
        return {}

def vector_search(query: str, db: Session, filters: Dict[str, Any] = None, limit: int = 50) -> Dict[str, float]:
    """Execute semantic vector search using FAISS."""
    if not query.strip():
        return {}
        
    query_vector = generate_embedding(query)
    if not query_vector:
        return {}
        
    # Retrieve top K from FAISS
    # We retrieve more than limit because we might filter some out
    faiss_results = vector_store.search(query_vector, top_k=limit * 3)
    
    if not faiss_results:
        return {}
        
    # If no filters, just return ranks and scores
    if not filters or not any(filters.values()):
        return {q_id: {"rank": i + 1, "score": float(score)} for i, (q_id, score) in enumerate(faiss_results[:limit])}
        
    # Apply metadata filters
    filtered_results = {}
    rank = 1
    
    for q_id, score in faiss_results:
        # Check metadata
        q = db.query(InterviewQuestion).join(InterviewRound).join(InterviewExperience).filter(
            InterviewQuestion.id == q_id
        )
        if filters.get("company"):
            q = q.filter(InterviewExperience.company.ilike(filters["company"]))
        if filters.get("role"):
            q = q.filter(InterviewExperience.role.ilike(filters["role"]))
        if filters.get("level"):
            q = q.filter(InterviewExperience.level.ilike(filters["level"]))
            
        if q.first():
            filtered_results[q_id] = {"rank": rank, "score": float(score)}
            rank += 1
            if rank > limit:
                break
                
    return filtered_results

def hybrid_search(query: str, filters: Dict[str, Any] = None, page: int = 1, page_size: int = 20, k: int = 60) -> Dict[str, Any]:
    """Execute hybrid search combining BM25 and Vector Search using RRF."""
    db = SessionLocal()
    try:
        limit = max(page * page_size, 100) # Fetch enough for pagination
        
        bm25_ranks = bm25_search(query, db, filters, limit=limit)
        vector_ranks = vector_search(query, db, filters, limit=limit)
        
        # Reciprocal Rank Fusion
        rrf_scores = {}
        all_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        
        for q_id in all_ids:
            score = 0.0
            if q_id in bm25_ranks:
                score += 1.0 / (k + bm25_ranks[q_id]["rank"])
            if q_id in vector_ranks:
                score += 1.0 / (k + vector_ranks[q_id]["rank"])
            rrf_scores[q_id] = score
            
        # Sort descending by RRF score
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_ids = [q_id for q_id, _ in sorted_results[start_idx:end_idx]]
        
        # Fetch full question details for the page
        questions_data = []
        if paginated_ids:
            # Maintain order
            cases = {q_id: i for i, q_id in enumerate(paginated_ids)}
            
            # Fetch with joins
            db_questions = db.query(InterviewQuestion, InterviewRound, InterviewExperience)\
                .join(InterviewRound, InterviewQuestion.round_id == InterviewRound.id)\
                .join(InterviewExperience, InterviewRound.experience_id == InterviewExperience.id)\
                .filter(InterviewQuestion.id.in_(paginated_ids))\
                .all()
                
            # Reorder
            db_questions.sort(key=lambda x: cases[x[0].id])
            
            for q, r, e in db_questions:
                questions_data.append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "round_name": r.round_name,
                    "company": e.company,
                    "role": e.role,
                    "level": e.level,
                    "experience_id": e.id,
                    "rrf_score": rrf_scores[q.id],
                    "bm25_rank": bm25_ranks[q.id]["rank"] if q.id in bm25_ranks else None,
                    "bm25_score": bm25_ranks[q.id]["score"] if q.id in bm25_ranks else None,
                    "vector_rank": vector_ranks[q.id]["rank"] if q.id in vector_ranks else None,
                    "vector_score": vector_ranks[q.id]["score"] if q.id in vector_ranks else None
                })
                
        return {
            "total": len(sorted_results),
            "page": page,
            "page_size": page_size,
            "results": questions_data
        }
    finally:
        db.close()
