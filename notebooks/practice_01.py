from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from scholar.config import settings

load_dotenv()

model = ChatGoogleGenerativeAI(
    model=settings.chat_model,
)

response = model.invoke("What is the capital city of Nepal?")
print(response)
