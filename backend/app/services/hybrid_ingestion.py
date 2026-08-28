import logging
import json
import uuid
import random
import re
import requests
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_models import User, InterviewExperience, InterviewRound, InterviewQuestion
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import vector_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)

TARGET_LEETCODE_RECORDS = 500
TARGET_SYNTHETIC_RECORDS = 2000

COMPANIES = ["Google", "Meta", "Amazon", "Apple", "Netflix", "Microsoft", "Uber", "Airbnb", "Stripe", "Databricks", "Snowflake", "Palantir", "Tesla", "LinkedIn", "Twitter", "Snap", "ByteDance", "Doordash", "Instacart", "Coinbase", "Robinhood", "Atlassian", "Block", "Nvidia", "Adobe", "Salesforce"]
ROLES = ["Software Engineer", "Senior Software Engineer", "Staff Software Engineer", "Backend Engineer", "Frontend Engineer", "Full Stack Engineer", "Machine Learning Engineer", "Data Engineer", "DevOps Engineer", "Site Reliability Engineer", "Product Manager", "Engineering Manager"]
LEVELS = ["Entry Level", "L3", "L4", "L5", "L6", "Mid-Level", "Senior", "Staff", "Principal", "SDE I", "SDE II", "SDE III"]
TOPICS = ["System Design", "Dynamic Programming", "Graphs", "Trees", "Arrays", "String Manipulation", "Concurrency", "Behavioral", "Leadership Principles", "API Design", "Database Design", "Kubernetes", "AWS", "Machine Learning", "Product Sense"]

QUESTIONS_BANK = {
    "coding": [
        "Implement an LRU Cache.", "Merge K Sorted Lists.", "Two Sum.", "Longest Substring Without Repeating Characters.", "Add Two Numbers.",
        "Median of Two Sorted Arrays.", "Regular Expression Matching.", "Container With Most Water.", "3Sum.", "Letter Combinations of a Phone Number.",
        "Remove Nth Node From End of List.", "Valid Parentheses.", "Merge Two Sorted Lists.", "Generate Parentheses.", "Merge Intervals.",
        "Search in Rotated Sorted Array.", "Trapping Rain Water.", "Permutations.", "Rotate Image.", "Group Anagrams.",
        "Maximum Subarray.", "Spiral Matrix.", "Jump Game.", "Merge Intervals.", "Insert Interval.", "Unique Paths.", "Climbing Stairs.",
        "Edit Distance.", "Minimum Window Substring.", "Word Search.", "Decode Ways.", "Validate Binary Search Tree.", "Binary Tree Level Order Traversal.",
        "Construct Binary Tree from Preorder and Inorder Traversal.", "Best Time to Buy and Sell Stock.", "Word Ladder.", "Longest Consecutive Sequence."
    ],
    "system_design": [
        "Design Instagram.", "Design Twitter.", "Design Uber / Lyft.", "Design a URL Shortener (TinyURL).", "Design WhatsApp / Messenger.",
        "Design Netflix.", "Design YouTube.", "Design Amazon/E-commerce platform.", "Design Google Drive.", "Design a Web Crawler.",
        "Design Ticketmaster.", "Design a distributed cache.", "Design a rate limiter.", "Design a key-value store.", "Design a real-time leaderboard."
    ],
    "behavioral": [
        "Tell me about a time you had a conflict with a coworker.", "Describe a situation where you had to meet a tight deadline.",
        "Tell me about a time you failed and what you learned.", "Why do you want to work here?", "Give an example of a time you showed leadership.",
        "Tell me about a time you had to learn a new technology quickly.", "Describe a complex project you worked on recently.",
        "How do you handle disagreement with a manager?", "Tell me about a time you received negative feedback.",
        "What is your greatest weakness?", "Where do you see yourself in 5 years?", "Tell me about a time you went above and beyond."
    ]
}

def wipe_database():
    logger.info("Wiping existing database by deleting the database file...")
    
    # Close any open connections? The SessionLocal hasn't been instantiated yet in the main flow.
    db_path = "viva_verse_v3.db"
    
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            logger.info("Deleted viva_verse_v3.db.")
        except Exception as e:
            logger.error(f"Could not delete DB file: {e}")
            
    # Wipe FAISS index
    if os.path.exists("faiss_index.bin"):
        os.remove("faiss_index.bin")
        vector_store.index = None
        
    logger.info("Database and vector index wiped successfully.")

def parse_leetcode_markdown_to_rounds(content: str) -> List[Dict[str, Any]]:
    rounds = []
    # Simple heuristic: split by keywords like "Round", "Phone Screen", "Onsite"
    sections = re.split(r'(?i)(?=\b(Round \d|Phone Screen|Onsite \d|Technical Interview|System Design Round|Behavioral)\b)', content)
    
    if len(sections) < 2:
        # If no explicit rounds found, create a generic one and dump everything
        rounds.append({
            "round_name": "General Interview",
            "notes": content[:1000],
            "questions": extract_questions_from_text(content)
        })
        return rounds

    for i in range(1, len(sections), 2):
        round_name = sections[i].strip()
        round_content = sections[i+1].strip() if i+1 < len(sections) else ""
        
        rounds.append({
            "round_name": round_name[:250],
            "notes": round_content[:1000],
            "questions": extract_questions_from_text(round_content)
        })
        
    return rounds

def extract_questions_from_text(text: str) -> List[Dict[str, str]]:
    questions = []
    # Look for numbered lists (e.g., "1. How to...", "2. Implement...")
    matches = re.finditer(r'(?:^|\n)\s*\d+\.\s*(.*?)(?=\n\s*\d+\.|\n\n|$)', text, re.DOTALL)
    for match in matches:
        q_text = match.group(1).strip().replace('\n', ' ')
        if len(q_text) > 10 and len(q_text) < 500:
            questions.append({"question_text": q_text})
            
    # If no numbered list found, try to extract LeetCode problem names in quotes or Capitalized
    if not questions:
        lc_matches = re.findall(r'"([^"]+)"|(?:\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b)', text)
        for m in lc_matches:
            q = m[0] if isinstance(m, tuple) and m[0] else m
            if q and len(q) > 10 and len(q) < 100:
                questions.append({"question_text": q.strip()})
                
    # If still nothing, just put a generic placeholder
    if not questions:
        questions.append({"question_text": "Discussed past experience and general technical questions."})
        
    return questions[:5] # limit to 5 questions per round

def fetch_leetcode_data() -> List[Dict[str, Any]]:
    logger.info("Fetching real data from LeetCode Discuss...")
    records = []
    skip = 0
    first = 50
    url = 'https://leetcode.com/graphql'
    query = '''
    query categoryTopicList($categories: [String!]!, $first: Int!, $skip: Int!) {
      categoryTopicList(categories: $categories, first: $first, skip: $skip) {
        edges {
          node {
            title
            post {
              content
            }
          }
        }
      }
    }
    '''
    
    while len(records) < TARGET_LEETCODE_RECORDS:
        variables = {'categories': ['interview-experience'], 'first': first, 'skip': skip}
        try:
            res = requests.post(url, json={'query': query, 'variables': variables}, headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
            data = res.json()
            edges = data.get('data', {}).get('categoryTopicList', {}).get('edges', [])
            if not edges: break
                
            for edge in edges:
                title = edge['node'].get('title', '')
                content = edge['node'].get('post', {}).get('content', '')
                if not content or len(content) < 50: continue
                    
                company = "Unknown"
                for c in COMPANIES:
                    if c.lower() in title.lower():
                        company = c
                        break
                
                role = "Software Engineer"
                for r in ["SDE", "SWE", "Engineer", "Data", "Manager", "Frontend", "Backend"]:
                    if r.lower() in title.lower(): role = r
                        
                level = "Mid-Level"
                match = re.search(r'[L|E]\d', title)
                if match: level = match.group()
                        
                records.append({
                    "company": company,
                    "role": role,
                    "level": level,
                    "overall_experience": content[:500] + "... [Parsed to Rounds]",
                    "source": "leetcode",
                    "topics": "Algorithms, Data Structures",
                    "rounds": parse_leetcode_markdown_to_rounds(content)
                })
                if len(records) >= TARGET_LEETCODE_RECORDS: break
            skip += first
        except Exception as e:
            logger.error(f"LeetCode fetch error: {e}")
            break
            
    logger.info(f"Fetched {len(records)} records from LeetCode.")
    return records

def generate_synthetic_data() -> List[Dict[str, Any]]:
    logger.info(f"Generating {TARGET_SYNTHETIC_RECORDS} deep synthetic records...")
    records = []
    
    for _ in range(TARGET_SYNTHETIC_RECORDS):
        company = random.choice(COMPANIES)
        role = random.choice(ROLES)
        level = random.choice(LEVELS)
        source = random.choice(["glassdoor", "blind"])
        
        num_rounds = random.randint(3, 5)
        rounds = []
        
        # Round 1: Recruiter / Behavioral
        rounds.append({
            "round_name": "Recruiter Screen",
            "notes": "Standard 30 min chat with recruiter about past experience, timeline, and expectations.",
            "questions": [{"question_text": random.choice(QUESTIONS_BANK["behavioral"])}]
        })
        
        # Middle rounds: Coding & System Design
        for r_idx in range(2, num_rounds):
            round_type = random.choice(["Coding", "System Design"])
            if round_type == "Coding":
                rounds.append({
                    "round_name": f"Technical Round {r_idx - 1} - Algorithms",
                    "notes": f"45 minute technical interview over CoderPad. Interviewer was friendly but strict on time.",
                    "questions": [{"question_text": random.choice(QUESTIONS_BANK["coding"])}, {"question_text": random.choice(QUESTIONS_BANK["coding"])}]
                })
            else:
                rounds.append({
                    "round_name": "System Design Round",
                    "notes": "Deep dive into architecture, scaling, and tradeoffs. Used a virtual whiteboard.",
                    "questions": [{"question_text": random.choice(QUESTIONS_BANK["system_design"])}]
                })
                
        # Final round: Behavioral / Hiring Manager
        rounds.append({
            "round_name": "Hiring Manager / Behavioral",
            "notes": "Met with the HM. Mostly focused on culture fit and conflict resolution.",
            "questions": [{"question_text": random.choice(QUESTIONS_BANK["behavioral"])}, {"question_text": random.choice(QUESTIONS_BANK["behavioral"])}]
        })
        
        overall = f"Just finished the {company} loop for {level} {role}. Overall a {random.choice(['challenging', 'smooth', 'tiring', 'great'])} experience."
        if source == "blind": overall = f"TC or GTFO. " + overall + f" Anyone know the typical band for {level} here?"
            
        records.append({
            "company": company,
            "role": role,
            "level": level,
            "overall_experience": overall,
            "source": source,
            "topics": f"{random.choice(TOPICS)}, {random.choice(TOPICS)}",
            "rounds": rounds
        })
        
    return records

def run_hybrid_ingestion():
    wipe_database()
    # Need to re-create schema since file was deleted
    from app.database import engine
    from app.database_models import Base
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        system_user = db.query(User).filter(User.username == "System Ingestion").first()
        if not system_user:
            system_user = User(username="System Ingestion", email="system@vivaverse.com", hashed_password="pw", role="admin")
            db.add(system_user)
            db.commit()
            db.refresh(system_user)

        all_records = fetch_leetcode_data() + generate_synthetic_data()
        random.shuffle(all_records)
        
        batch_size = 50 # Smaller batch size because these are deep objects
        total_inserted = 0
        
        for i in range(0, len(all_records), batch_size):
            batch = all_records[i:i+batch_size]
            db_exps = []
            texts_to_embed = []
            
            for data in batch:
                exp = InterviewExperience(
                    user_id=system_user.id,
                    company=data["company"],
                    role=data["role"],
                    level=data["level"],
                    overall_experience=data["overall_experience"],
                    source=data["source"],
                    topics=data["topics"]
                )
                db.add(exp)
                db.flush()
                
                # Add rounds and questions
                full_text_chunks = [f"{exp.company} {exp.role} {exp.level} {exp.overall_experience}"]
                
                for r_data in data["rounds"]:
                    round_obj = InterviewRound(
                        experience_id=exp.id,
                        round_name=r_data["round_name"],
                        notes=r_data["notes"]
                    )
                    db.add(round_obj)
                    db.flush()
                    full_text_chunks.append(f"{round_obj.round_name}: {round_obj.notes}")
                    
                    for q_data in r_data["questions"]:
                        q_obj = InterviewQuestion(
                            round_id=round_obj.id,
                            question_text=q_data["question_text"]
                        )
                        db.add(q_obj)
                        full_text_chunks.append(q_obj.question_text)
                        
                db_exps.append(exp)
                texts_to_embed.append(" | ".join(full_text_chunks))
                
            db.commit()
            
            # Embed batch
            try:
                # Re-initialize vector store if needed (since we wiped the file)
                if not vector_store.index:
                    vector_store._init_index()
                    
                embeddings = generate_embeddings(texts_to_embed)
                for exp, emb in zip(db_exps, embeddings):
                    if emb:
                        exp.embedding = json.dumps(emb)
                        vector_store.add_embedding(exp.id, emb)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to embed batch: {e}")
                
            total_inserted += len(batch)
            logger.info(f"Ingested {total_inserted}/{len(all_records)} deep records...")
            
        logger.info("Deep hybrid ingestion completed successfully!")
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_hybrid_ingestion()
