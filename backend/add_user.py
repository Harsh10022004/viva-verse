import sys
import os

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app.database_models import User
from app.utils.auth import get_password_hash

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def add_user(username, email, password, role="student"):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists.")
            return

        hashed_password = get_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role=role
        )
        db.add(new_user)
        db.commit()
        print(f"Successfully added {role} user: {username}")
    except Exception as e:
        print(f"Error adding user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Add a new user to the Viva Verse database")
    parser.add_argument("username", help="Username for the new user")
    parser.add_argument("email", help="Email for the new user")
    parser.add_argument("password", help="Password for the new user")
    parser.add_argument("--role", default="student", choices=["student", "examiner"], help="Role of the user (default: student)")

    args = parser.parse_args()
    add_user(args.username, args.email, args.password, args.role)
