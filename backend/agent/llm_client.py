import os
from langchain_google_genai import ChatGoogleGenerativeAI

# For testing today, you can set it inline.
# (Make sure to move this to a .env file before putting this on GitHub!)
os.environ["GOOGLE_API_KEY"] = "AIzaSyC9MfBEJDW6rv0LMjrE3b0veSnwTXHk_5Q"

# Use Gemini 2.5 Flash: It's extremely fast and handles JSON perfectly
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)