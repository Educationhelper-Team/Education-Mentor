import google.generativeai as genai
import os

# --- Configuration and Initialization ---
# Replace 'YOUR_API_KEY' with your actual API key
genai.configure(api_key="AIzaSyAi7qQtzC6SBUUGDMDBtR7z-DBiS0-1hwM")

# Create the Generative Model
model = genai.GenerativeModel('gemini-1.5-flash')

# Gamification data store
user_data = {
    "points": 0,
    "level": 1,
    "points_to_next_level": 100,
    "current_mode": "general", # Tracks the current conversational mode
    "quiz_topic": None, # Stores the topic for a mock test
}

# --- System Prompt for a Multi-functional Bot ---
system_prompt = (
    "You are a versatile educational AI assistant. Your role is to handle multiple learning requests. "
    "Here are your key features:\n"
    "1.  **Syllabus & Study Plans**: When a user asks for a syllabus or study plan, provide a structured list of topics, estimated time, and a week-by-week schedule.\n"
    "2.  **Study Notes & Formulas**: When a user asks for notes or formulas on a topic, provide a concise summary with key points or a clear list of formulas with variable explanations.\n"
    "3.  **Doubt Solving**: When a user has a doubt, provide a clear, step-by-step explanation. Break down complex concepts and use analogies.\n"
    "4.  **Practice & Mock Tests**: When a user asks for a practice test, generate a single multiple-choice question with a correct answer. Wait for the user's answer, then provide feedback and ask the next question.\n"
    "5.  **Gamification**: Encourage the user to earn points for correct answers and provide positive reinforcement. Do not display points or levels yourself; the program will handle that.\n"
    "Your responses should be encouraging and concise. Based on the user's request, you will switch between these modes. After answering a question, always ask the user what they'd like to do next."
)

chat = model.start_chat(history=[
    {
        "role": "user",
        "parts": [system_prompt]
    },
    {
        "role": "model",
        "parts": ["Hello! I'm a comprehensive learning assistant. What can I help you with today? You can ask for a syllabus, study notes, a practice test, or a doubt. 💡"]
    }
])

# --- Helper Functions ---
def update_points_and_level(points_earned):
    """Updates the user's points and level."""
    global user_data
    user_data["points"] += points_earned
    
    if user_data["points"] >= user_data["points_to_next_level"]:
        user_data["level"] += 1
        user_data["points"] -= user_data["points_to_next_level"]
        user_data["points_to_next_level"] *= 2  # Double points needed for the next level
        print(f"\n🌟 CONGRATULATIONS! You've reached Level {user_data['level']}! Keep up the great work!")

def get_ai_response(prompt):
    """Sends a prompt to the AI and returns the text response."""
    try:
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

def handle_user_input(user_input):
    """Parses user input to determine the chatbot's mode."""
    user_input_lower = user_input.lower()
    
    if "syllabus" in user_input_lower or "study plan" in user_input_lower:
        user_data["current_mode"] = "syllabus"
        return "Syllabus"
    elif "notes" in user_input_lower or "formulas" in user_input_lower:
        user_data["current_mode"] = "notes"
        return "Notes"
    elif "test" in user_input_lower or "quiz" in user_input_lower:
        user_data["current_mode"] = "quiz"
        user_data["quiz_topic"] = user_input.replace("test", "").replace("quiz", "").strip()
        return "Quiz"
    elif "doubt" in user_input_lower or "question" in user_input_lower or "explain" in user_input_lower:
        user_data["current_mode"] = "doubt_solving"
        return "Doubt"
    else:
        # If no specific command is found, assume it's part of a current session or a general question
        return "General"

# --- Main Chatbot Loop ---
def main():
    """The main function to run the combined chatbot."""
    print("Welcome to the All-in-One Educational Chatbot! 🎓")
    print("I can help you with syllabi, study notes, mock tests, and more.")
    print("Type 'exit' to end the session.")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("\nGoodbye! Your final score is:", user_data["points"])
            print("You reached Level:", user_data["level"])
            break

        # Check for a mode change or a new request
        intent = handle_user_input(user_input)
        
        # Prepare the prompt based on the determined intent and current mode
        prompt = user_input

        # Handle the quiz mode specifically to track answers
        if user_data["current_mode"] == "quiz" and user_data["quiz_topic"] is not None:
            # The AI's response is already tailored for a quiz from the prompt
            response = get_ai_response(prompt)
            print(f"\nAssistant: {response}")
            
            # Simple check for a correct answer (can be more robust)
            # The AI should be prompted to say "Correct" or "Incorrect"
            if "correct" in response.lower():
                points = 20
                update_points_and_level(points)
                print(f"🎉 You earned {points} points!\n")
            
        else:
            # For all other modes, just get the response normally
            response = get_ai_response(prompt)
            print(f"\nAssistant: {response}")

        print(f"\nYour current score: {user_data['points']} | Level: {user_data['level']}\n")

if __name__ == "__main__":
    main()