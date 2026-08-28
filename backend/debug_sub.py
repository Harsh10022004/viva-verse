import os
import json
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_models import InterviewExperience, SearchSubscription

def debug_subscriptions():
    db = SessionLocal()
    try:
        # Get the latest experience
        latest_exp = db.query(InterviewExperience).order_by(InterviewExperience.created_at.desc()).first()
        if not latest_exp or not latest_exp.embedding:
            print("No valid latest experience found.")
            return

        print(f"\n--- DEBUG: Latest Post ---")
        print(f"ID: {latest_exp.id}")
        print(f"Role: {latest_exp.role} at {latest_exp.company}")
        print(f"Topics: {latest_exp.topics}")
        
        new_vector = np.array(json.loads(latest_exp.embedding), dtype=np.float32).reshape(1, -1)
        
        # Get all subscriptions
        subscriptions = db.query(SearchSubscription).all()
        print(f"\n--- DEBUG: Subscriptions ({len(subscriptions)} found) ---")
        
        for sub in subscriptions:
            print(f"\nEvaluating Subscription: '{sub.query_text}'")
            print(f"Threshold Benchmark: {sub.threshold_score:.4f}")
            
            if not sub.query_embedding:
                print(" -> Error: Subscription has no query embedding.")
                continue
                
            sub_vector = np.array(json.loads(sub.query_embedding), dtype=np.float32).reshape(1, -1)
            distance = float(np.sum((new_vector - sub_vector) ** 2))
            
            print(f"Calculated L2 Distance to Latest Post: {distance:.4f}")
            
            if distance <= sub.threshold_score:
                print(" -> RESULT: MATCH! (Distance <= Threshold)")
            else:
                print(" -> RESULT: NO MATCH (Distance > Threshold). Post is not semantically close enough.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_subscriptions()
