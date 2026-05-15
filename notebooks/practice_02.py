from textwrap import dedent

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

system_prompt = dedent("""You're an academic copywriter. Titles should be concise and engaging,
output should be a numbered list of three titles only """)
template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            system_prompt,
        ),
        ("human", "Create 3 creative titles for the following paper abstract: {abstract}"),
    ]
)

model = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=1)
messages = template.invoke(
    {
        "abstract": """We introduce a new family of generative models
called diffusion models, which gradually denoise random noise to produce samples.
We show that diffusion models achieve sample quality competitive with GANs on CIFAR-10 and ImageNet,
while being significantly more stable to train. Our key insight is that the reverse
diffusion process can be parameterized by a simple neural network trained with a denoising
score-matching objective."""
    }
)

response = model.invoke(messages)

print(response.content)
