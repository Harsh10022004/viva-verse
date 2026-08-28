import json
import numpy as np
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_models import SearchSubscription
from app.services.search_service import calculate_subscription_threshold

def update_existing_thresholds():
    db = SessionLocal()
    try:
        subscriptions = db.query(SearchSubscription).all()
        for sub in subscriptions:
            if not sub.query_embedding:
                continue
                
            sub_vector = json.loads(sub.query_embedding)
            # Recalculate using the new loosened math
            new_threshold = calculate_subscription_threshold([sub_vector])
            print(f"Updating '{sub.query_text}': {sub.threshold_score:.4f} -> {new_threshold:.4f}")
            sub.threshold_score = new_threshold
            
        db.commit()
        print("Done updating subscriptions.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_existing_thresholds()
