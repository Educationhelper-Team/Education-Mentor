import os

GROQ_API_KEY = os.getenv("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")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable is not set.")   