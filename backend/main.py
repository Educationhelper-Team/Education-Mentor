import os
import json
import random
from typing import Dict, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, validator
from dotenv import load_dotenv
from groq import Groq, APIConnectionError, AuthenticationError, RateLimitError, APIError
import uvicorn

   




# Load environment variables
load_dotenv()

# FastAPI App Initialization
app = FastAPI(
    title="AI-Powered Learning Assistant for Students",
    description="An AI-driven web app to automate study materials, generate courses, and teach students through AI-powered explanations, videos, and study notes.",
    version="1.0.0"
)




# Mount static files
# You need a 'static' directory with your HTML files for these to work.
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login.html", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})





# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Pydantic Models
class ChatPayload(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

class SyllabusPayload(BaseModel):
    subject: str
    level: str

    @validator('subject')
    def subject_must_exist(cls, v):
        if v.lower() not in ['math', 'science', 'history', 'languages']:
            raise ValueError('Subject must be math, science, history, or languages')
        return v.lower()

    @validator('level')
    def level_must_exist(cls, v):
        if v.lower() not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Level must be beginner, intermediate, or advanced')
        return v.lower()

class NotesPayload(BaseModel):
    topic: str
    student_id: str | None = None

class TestPayload(BaseModel):
    subject: str
    student_id: str | None = None

    @validator('subject')
    def subject_must_exist(cls, v):
        if v.lower() not in ['math', 'science']:
            raise ValueError('Subject must be math or science for tests')
        return v.lower()

class VideoPayload(BaseModel):
    topic: str
    student_id: str | None = None

# Resource Database
LLM_MODEL = "llama3-70b-8192"

def load_resources():
    """Loads static resources for the learning assistant."""
    resources = {
        "subjects": {
            "math": {"levels": ["beginner", "intermediate", "advanced"], "content": "Mathematics: Algebra, Calculus, Geometry"},
            "science": {"levels": ["beginner", "intermediate", "advanced"], "content": "Science: Physics, Chemistry, Biology"},
            "history": {"levels": ["beginner", "intermediate", "advanced"], "content": "History: World History, Ancient Civilizations"},
            "languages": {"levels": ["beginner", "intermediate", "advanced"], "content": "Languages: English, Hindi, Spanish"}
        },
        "study_tips": {
            "concentration": "Use the Pomodoro technique: Study for 25 minutes, then take a 5-minute break.",
            "note_taking": "Try the Cornell method: Divide your page into sections for notes, cues, and summaries.",
            "exam_prep": "Practice past papers and review mistakes to improve understanding."
        },
        "online_resources": {
            "math": {"name": "Khan Academy", "url": "https://www.khanacademy.org/math"},
            "science": {"name": "Coursera", "url": "https://www.coursera.org/browse/physical-science-and-engineering"},
            "general": {"name": "Wikipedia", "url": "https://www.wikipedia.org/"}
        },
        "quiz_topics": {
            "math": ["What is the derivative of x^2?", "Solve 2x + 3 = 7", "What is 5!?", "Solve x^2 - 4 = 0", "What is Pythagoras theorem?"],
            "science": ["What is Newton's first law?", "What is the chemical symbol for water?", "What is photosynthesis?", "What is the boiling point of water?", "What gas do plants absorb?"]
        },
        "badges": ["Beginner Badge", "Topic Master", "Mock Test Ace", "Subject Expert"],
        "achievements": ["Completed first quiz", "Studied 5 days in a row", "Mastered a subject"],
        "daily_challenges": ["Solve 5 math problems", "Read a history chapter", "Practice 10 vocabulary words"],
        "weekly_challenges": ["Complete a mock test", "Watch 3 video lectures", "Write a summary"]
    }
    return resources

RESOURCES = load_resources()

# Master System Prompts
MASTER_SYSTEM_PROMPTS = {
    "DEFAULT": {
        "persona": """
        You are "EduMentor" (Your AI Learning Assistant), an AI-powered assistant for students.
        Your core principles are clarity, encouragement, and personalized support.
        Speak in the user's language (Hindi, Hinglish, English, etc.).
        Avoid jargon and long paragraphs. Be a motivating, knowledgeable voice of support.
        You are the best learning companion.
        """,
        "rules": """
        - Respond directly in the user's language without repeating their question
        - If they ask in English, respond in English
        - If they ask in Hindi, respond in Hindi  
        - If they ask in Marathi, respond in Marathi
        - Do NOT translate their question first - just answer directly
        - Keep responses concise and helpful
        """
    },
    "EXPLANATION": {
        "persona": "You are 'EduMentor', a knowledge explainer AI. Your tone is clear, step-by-step, and patient.",
        "rules": """
        **RESPONSE MUST FOLLOW THIS 3-PART STRUCTURE:**
        1. **Acknowledge (1 Sentence MAX):** Briefly confirm the topic.
        2. **Explain (2-3 Sentences MAX):** Break down the concept simply with an example.
        3. **Practice (1 Sentence MAX):** Suggest a quick practice or resource.
        **ABSOLUTE RULES:** Be brief, stick to the query, always suggest a resource or practice.
        """
    },
    "VIDEO": {
        "persona": "You are 'EduMentor', a video lecture generator AI. Your tone is engaging and educational.",
        "rules": """
        **RESPONSE MUST BE A DESCRIPTION:**
        - Describe an animated video lesson for the given topic.
        - Include step-by-step concept explanation and visuals.
        - Keep it concise and engaging.
        """
    },
    "NOTES": {
        "persona": "You are 'EduMentor', a study notes generator AI. Your tone is clear and structured.",
        "rules": """
        **RESPONSE MUST FOLLOW THIS STRUCTURE:**
        - Provide detailed notes for the topic.
        - Include summary notes for quick revision.
        - Suggest formula sheets or shortcuts if applicable.
        """
    },
    "TEST": {
        "persona": "You are 'EduMentor', a practice test generator AI. Your tone is instructional and supportive.",
        "rules": """
        **RESPONSE MUST INCLUDE:**
        - 5 topic-wise MCQs or PYQs.
        - Detailed explanations for answers.
        - Track progress and suggest weak areas.
        """
    },
    "DOUBT_SOLVING": {
        "persona": "You are 'EduMentor', a doubt-solving AI chatbot. Your tone is patient and helpful.",
        "rules": """
        **RESPONSE MUST BE:**
        - Answer the doubt directly with a step-by-step solution.
        - Provide additional resources if needed.
        - Encourage further questions.
        """
    },
    "MOTIVATION": {
        "persona": "You are 'EduMentor', a motivational AI coach. Your tone is warm and uplifting.",
        "rules": """
        **GOAL: SHORT, ENCOURAGING. Aim for 1-2 sentences.**
        1. **VALIDATE & MOTIVATE:** Make them feel capable and supported.
        2. **GENTLE SUGGESTION:** Add a quick tip if needed.
        **AVOID:** Pressure or minimizing efforts.
        """
    },
    "SYLLABUS": {
        "persona": "You are 'EduMentor', a syllabus generator AI. Your tone is structured and comprehensive.",
        "rules": """
        **RESPONSE MUST FOLLOW THIS STRUCTURE:**
        - Course Description
        - Learning Objectives
        - Week-by-week Topics
        - Suggested Readings
        - Final Assessment
        """
    },
}

# EduMentor Chatbot Class
class EduMentorChatbot:
    """The main class for the EduMentor Chatbot, managing state, intent, and responses."""
    def __init__(self, client: Groq):
        """Initializes the chatbot's state."""
        self.client = client
        self.chat_history: List[Dict] = []
        self.study_status = "active"
        self.current_subject = None
        self.student_progress = {}
        self.xp = 0
        self.achievements = []

    def _call_groq_api(self, messages: list, temperature: float = 0.4, max_tokens: int = 1000) -> str:
        """Helper function to call the Groq API with robust error handling."""
        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except RateLimitError:
            return "⚠️ Too many requests. Please try again later."
        except AuthenticationError:
            return "⚠️ Invalid API key. Please contact the administrator."
        except APIError as e:
            print(f"API Error: {e}")
            return "⚠️ Technical issue. Please try again."
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "⚠️ An error occurred. Please try again."

    def classify_intent(self, user_input: str) -> str:
        """Classifies the user's intent."""
        intents = ["EXPLANATION", "VIDEO", "NOTES", "TEST", "DOUBT_SOLVING", "MOTIVATION", "SYLLABUS", "DEFAULT"]
        classification_prompt = f"""
        Analyze the user's message and classify its primary intent into ONE of the following categories: {', '.join(intents)}.
        User's message: "{user_input}"
        Classification:
        """
        messages = [{"role": "user", "content": classification_prompt}]
        response = self._call_groq_api(messages, temperature=0.0, max_tokens=20)
        intent = response.strip().upper().replace("'", "").replace('"', "")
        return intent if intent in intents else "DEFAULT"

    def _handle_special_commands(self, user_input: str) -> str | None:
        """Handles special slash commands."""
        if user_input.lower().startswith("/subject"):
            try:
                self.current_subject = user_input.split(" ", 1)[1].strip().lower()
                if self.current_subject not in RESOURCES["subjects"]:
                    return "Invalid subject. Use math, science, history, or languages."
                return f"Great! Subject set to {self.current_subject}."
            except IndexError:
                return "Please provide a subject, e.g., /subject math."
        return None

    def award_badge(self, action: str, student_id: str | None = None):
        """Awards badges and XP based on actions."""
        if action == "quiz_completed":
            self.xp += 50
            if "Beginner Badge" not in self.achievements:
                self.achievements.append("Beginner Badge")
        elif action == "test_completed":
            self.xp += 100
            if "Mock Test Ace" not in self.achievements:
                self.achievements.append("Mock Test Ace")
        if student_id:
            self.student_progress[student_id] = self.student_progress.get(student_id, {})
            self.student_progress[student_id]["xp"] = self.student_progress.get(student_id, {}).get("xp", 0) + (50 if action == "quiz_completed" else 100)

    def generate_syllabus(self, subject: str, level: str) -> str:
        """Generates a structured syllabus using LLM."""
        prompt = f"""
        Create a comprehensive, university-level syllabus for a course titled "{level} {subject}".
        Follow this structure:
        - Course Description
        - Learning Objectives
        - Week-by-week Topics (8 weeks)
        - Suggested Readings
        - Final Assessment
        """
        messages = [
            {"role": "system", "content": MASTER_SYSTEM_PROMPTS["SYLLABUS"]["persona"] + "\n" + MASTER_SYSTEM_PROMPTS["SYLLABUS"]["rules"]},
            {"role": "user", "content": prompt}
        ]
        return self._call_groq_api(messages)

    def generate_video_description(self, topic: str) -> str:
        """Generates a video lesson description using LLM."""
        prompt = f"""
        Describe an animated video lesson for the topic "{topic}".
        Include:
        - A brief introduction to the topic
        - Step-by-step explanation of key concepts
        - Description of visuals (e.g., diagrams, animations)
        - A closing summary
        Keep it concise and engaging.
        """
        messages = [
            {"role": "system", "content": MASTER_SYSTEM_PROMPTS["VIDEO"]["persona"] + "\n" + MASTER_SYSTEM_PROMPTS["VIDEO"]["rules"]},
            {"role": "user", "content": prompt}
        ]
        return self._call_groq_api(messages)

    def generate_notes(self, topic: str) -> str:
        """Generates detailed study notes using LLM."""
        prompt = f"""
        Generate detailed study notes for the topic "{topic}".
        Structure the notes as follows:
        - Introduction: Brief overview of the topic
        - Key Concepts: Detailed explanation with examples
        - Summary: Concise recap of main points
        - Formulas/Shortcuts: Include if applicable
        """
        messages = [
            {"role": "system", "content": MASTER_SYSTEM_PROMPTS["NOTES"]["persona"] + "\n" + MASTER_SYSTEM_PROMPTS["NOTES"]["rules"]},
            {"role": "user", "content": prompt}
        ]
        return self._call_groq_api(messages)

    def generate_test(self, subject: str, student_id: str | None = None) -> str:
        """Generates practice test with MCQs using LLM."""
        prompt = f"""
        Generate a practice test for {subject} with 5 multiple-choice questions.
        For each question, provide:
        - The question
        - Four answer options (A, B, C, D)
        - The correct answer
        - A brief explanation of the correct answer
        Suggest one weak area for improvement based on the subject.
        """
        messages = [
            {"role": "system", "content": MASTER_SYSTEM_PROMPTS["TEST"]["persona"] + "\n" + MASTER_SYSTEM_PROMPTS["TEST"]["rules"]},
            {"role": "user", "content": prompt}
        ]
        test = self._call_groq_api(messages)
        self.award_badge("test_completed", student_id)
        if student_id:
            self.student_progress[student_id] = self.student_progress.get(student_id, {})
            self.student_progress[student_id][subject] = self.student_progress.get(student_id, {}).get(subject, {})
            self.student_progress[student_id][subject]["attempts"] = self.student_progress[student_id][subject].get("attempts", 0) + 1
            self.student_progress[student_id][subject]["weak_areas"] = f"{subject} fundamentals"
        return test

    def process_message(self, user_input: str) -> str:
        """Processes user input and generates response."""
        command_response = self._handle_special_commands(user_input)
        if command_response:
            return command_response

        intent = self.classify_intent(user_input)
        prompt_data = MASTER_SYSTEM_PROMPTS.get(intent, MASTER_SYSTEM_PROMPTS["DEFAULT"])
        contextual_info = f"""
        CURRENT CONTEXT:
        - Study Status: {self.study_status}
        - Current Subject: {self.current_subject or 'Not Set'}
        - Resources: {json.dumps(RESOURCES)}
        - XP: {self.xp}
        - Achievements: {json.dumps(self.achievements)}
        """
        anti_repetition_rule = "CRITICAL: Do NOT repeat or translate the user's question. Answer directly."
        full_system_prompt = f"{prompt_data['persona']}\n{contextual_info}\nRULES:\n{prompt_data['rules']}\n{anti_repetition_rule}"

        messages = [
            {"role": "system", "content": full_system_prompt},
            *self.chat_history[-6:],
            {"role": "user", "content": user_input}
        ]

        response_text = self._call_groq_api(messages)
        self.chat_history.extend([{"role": "user", "content": user_input}, {"role": "assistant", "content": response_text}])
        return response_text

# Initialize the Assistant
try:
    groq_api_key = "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"
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY not found. Set it in a .env file.")

    client = Groq(api_key=groq_api_key)
    # The call to client.models.list() validates the key.
    client.models.list()
    print("✅ Groq API key validated.")

    assistant = EduMentorChatbot(client)
    print("📚 EduMentor - Your AI Learning Assistant is ready. 📚")

except (ValueError, AuthenticationError, APIConnectionError, APIError) as e:
    print(f"❌ Fatal Error: {e}")
    print("EduMentor cannot start. Check your Groq API key.")
    assistant = None
except Exception as e:
    print(f"❌ Critical Error: {type(e).__name__} - {e}")
    print("EduMentor cannot start due to an unforeseen issue.")
    assistant = None

# API Endpoints
@app.get("/")
def root():
    return {"message": "📚 EduMentor API is running! 🚀"}

@app.post("/chat")
async def chat(payload: ChatPayload):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    user_input = payload.message
    if not user_input.strip():
        return ChatResponse(reply="Please ask something.")
    try:
        response = assistant.process_message(user_input)
        return ChatResponse(reply=response)
    except Exception as e:
        print(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal error during chat processing.")

@app.post("/syllabus")
async def generate_syllabus_endpoint(payload: SyllabusPayload):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    try:
        return {"syllabus": assistant.generate_syllabus(payload.subject, payload.level)}
    except Exception as e:
        print(f"Error generating syllabus: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate syllabus.")

@app.post("/video")
async def generate_video(payload: VideoPayload):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    try:
        return {"video_description": assistant.generate_video_description(payload.topic)}
    except Exception as e:
        print(f"Error generating video: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate video description.")

@app.post("/notes")
async def generate_notes(payload: NotesPayload):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    try:
        return {"notes": assistant.generate_notes(payload.topic)}
    except Exception as e:
        print(f"Error generating notes: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate notes.")

@app.post("/test")
async def generate_test_endpoint(payload: TestPayload):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    try:
        return {"test": assistant.generate_test(payload.subject, payload.student_id)}
    except Exception as e:
        print(f"Error generating test: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate test.")

@app.get("/achievements")
def get_achievements():
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    return {"achievements": assistant.achievements, "xp": assistant.xp}

@app.get("/challenges")
def get_challenges():
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    return {"daily": random.choice(RESOURCES["daily_challenges"]), "weekly": random.choice(RESOURCES["weekly_challenges"])}

@app.get("/progress/{student_id}")
def get_progress(student_id: str):
    if not assistant:
        raise HTTPException(status_code=500, detail="Chatbot not initialized. Please check server logs.")
    return {"progress": assistant.student_progress.get(student_id, {})}

# Server Startup
if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8000, reload=True)