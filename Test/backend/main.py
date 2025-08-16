from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import json


from fastapi import FastAPI

app = FastAPI()

@app.get("/")   # 👈 this creates a homepage route
def home():
    return {"message": "Welcome to EduMentor API 🎓"}



# Initialize FastAPI application
app = FastAPI()

# IMPORTANT: Configure CORS (Cross-Origin Resource Sharing).
# This allows your frontend running on one domain (or localhost)
# to make requests to this backend on another domain/port.
# For production, replace "*" with your frontend's specific domain.
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: For production, you must set this as an environment variable
# to keep your API key secure. Example: os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"

@app.post("/generate")
async def generate_content(request: Request):
    """
    Endpoint to receive a prompt from the frontend, call the Gemini API,
    and return the AI's response.
    
    The frontend should send a JSON body with 'prompt' and 'history'.
    Example payload:
    {
      "prompt": "Hello there!",
      "history": []
    }
    """
    try:
        # Get the JSON data from the request body
        data = await request.json()
        user_prompt = data.get('prompt')
        chat_history = data.get('history', [])

        if not user_prompt:
            # Return a 400 Bad Request error if the prompt is missing
            raise HTTPException(status_code=400, detail="Prompt is required")

        # Append the new user prompt to the chat history
        chat_history.append({"role": "user", "parts": [{"text": user_prompt}]})

        # Construct the payload for the Gemini API call
        payload = {
            "contents": chat_history,
            "generationConfig": {
                "temperature": 0.7,
            },
        }

        # Make the secure API call to Gemini using the backend
        headers = {"Content-Type": "application/json"}
        params = {"key": GEMINI_API_KEY}
        
        response = requests.post(GEMINI_API_URL, headers=headers, params=params, data=json.dumps(payload))
        response.raise_for_status()  # This will raise an HTTPError for bad responses

        api_response = response.json()

        if api_response.get('candidates'):
            ai_text = api_response['candidates'][0]['content']['parts'][0]['text']
            
            # Append the AI's response to the history
            chat_history.append({"role": "model", "parts": [{"text": ai_text}]})
            
            # Return the AI response and updated history to the frontend
            return {"response": ai_text, "history": chat_history}
        else:
            raise HTTPException(status_code=500, detail="Invalid response from AI model")

    except requests.exceptions.RequestException as e:
        # Handle errors that occur during the request to the Gemini API
        raise HTTPException(status_code=500, detail=f"API request failed: {e}")
    
    except Exception as e:
        # Catch all other unexpected errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# To run the backend, open your terminal and navigate to the directory of this file,
# then execute: uvicorn main:app --reload
