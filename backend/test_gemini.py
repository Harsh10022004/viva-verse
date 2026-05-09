import os
from dotenv import load_dotenv
from google import genai
import traceback

load_dotenv("c:\\Users\\ASUS\\Desktop\\BITS_CAP_101\\backend\\.env", override=True)
api_key = os.environ.get("GEMINI_API_KEY")

print(f"API Key found: {'Yes' if api_key else 'No'}, Length: {len(api_key) if api_key else 0}")

try:
    client = genai.Client(api_key=api_key)
    print("Client initialized")
    
    prompt = "Hello, generate a simple test question about Python."
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    print("Response text:", response.text.strip())
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
