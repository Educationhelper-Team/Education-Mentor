# A robust and correct FastAPI backend for a multi-subject AI assistant.
# This code handles conversation history to enable a "multitasker" AI.

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import json
import logging
from groq import Groq  # Import the Groq client
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")





# Set up logging for better error tracking
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI application
app = FastAPI(
    title="Multitasker AI Backend",
    description="A secure and robust backend for the AI assistant, handling all subject queries.",
    version="1.0.0",
)

# IMPORTANT: Configure CORS (Cross-Origin Resource Sharing).
# This is crucial for allowing your frontend (running on a different port)
# to make requests to this backend. For a production environment, you should
# replace the "*" with your specific frontend domain (e.g., "https://yourdomain.com").
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- Configuration ---
# NOTE: In a production environment, you must secure your API key by using
# environment variables. For local development, this is acceptable.
GROQ_API_KEY = "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"

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

@app.get("/")
def read_root():
    """
    A simple root endpoint to confirm the API is running.
    """
    return {"message": "AI Assistant Backend is running! Access the /docs endpoint for API documentation."}


@app.post("/generate")
async def generate_content(request: Request):
    """
    Endpoint to receive a prompt and conversation history from the frontend,
    call the Groq API, and return the AI's response.
    
    The frontend should send a JSON body with 'prompt' and 'history'.
    The 'history' field should be an array of objects representing the
    conversation so far, as formatted for the Groq API.
    
    Example payload:
    {
      "prompt": "Hello there!",
      "history": []
    }
    """
    try:
        data = await request.json()
        user_prompt = data.get('prompt')
        chat_history = data.get('history', [])

        if not user_prompt or user_prompt.strip() == "":
            logging.error("Received an empty prompt.")
            raise HTTPException(status_code=400, detail="Prompt is required and cannot be empty.")

        # Append the new user prompt to the chat history for context
        chat_history.append({"role": "user", "content": user_prompt})
        
        # Ensure the history only contains alternating user/model roles
        # This is a good practice to prevent API errors
        cleaned_history = []
        for i in range(len(chat_history)):
            current_role = chat_history[i]['role']
            if i > 0 and current_role == chat_history[i-1]['role']:
                # Merge consecutive messages from the same role
                cleaned_history[-1]['content'] += " " + chat_history[i]['content']
            else:
                cleaned_history.append(chat_history[i])
        
        # The final payload for the Groq API call
        
        try:
            chat_completion = client.chat.completions.create(
                messages=cleaned_history,
                model="llama3-8b-8192",  # You can choose a different Groq model here
                temperature=0.7,
                # Additional generation parameters can be added here
            )
            
            ai_text = chat_completion.choices[0].message.content
            
            # Append the new AI response to the history before sending it back
            chat_history.append({"role": "assistant", "content": ai_text})
            
            # Return the AI response and the updated full history
            return {"response": ai_text, "history": chat_history}

        except Exception as e:
            logging.error(f"Groq API request failed: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to connect to Groq service: {e}")

    except json.JSONDecodeError:
        logging.error("Invalid JSON format in the request body.")
        raise HTTPException(status_code=400, detail="Invalid JSON format in request body.")
    except HTTPException as http_exc:
        # Re-raise explicit HTTP exceptions
        raise http_exc
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

# To run the backend, open your terminal and navigate to the directory of this file,
# then execute: uvicorn main:app --reload
