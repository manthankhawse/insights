import os
from langchain_groq import ChatGroq

# For testing today, you can set it inline.
# (Make sure to move this to a .env file before putting this on GitHub!)
os.environ["GROQ_API_KEY"] = ""

# Use Gemini 2.5 Flash: It's extremely fast and handles JSON perfectly
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)