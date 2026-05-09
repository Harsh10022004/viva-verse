import os
import time
from dotenv import load_dotenv
from google import genai
import traceback

load_dotenv("c:\\Users\\ASUS\\Desktop\\BITS_CAP_101\\backend\\.env", override=True)
api_key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("Starting 6 sequential requests to simulate generate_questions...")
success_count = 0
for i in range(6):
    try:
        print(f"Request {i+1}...")
        prompt = f"Write a 1-sentence summary of the number {i}."
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        print(f"Success {i+1}: {response.text.strip()}")
        success_count += 1
    except Exception as e:
        print(f"Failed on request {i+1}: {type(e).__name__} - {str(e)}")
        # Let's see if waiting 10s is enough
        print("Waiting 10 seconds...")
        time.sleep(10)
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            print(f"Retry Success {i+1}: {response.text.strip()}")
            success_count += 1
        except Exception as e2:
            print(f"Retry Failed {i+1}: {str(e2)}")

print(f"Total Successful: {success_count}/6")
