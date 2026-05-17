import os
from textwrap import dedent

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_groq import ChatGroq

# from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich import print

load_dotenv()

loader = PyMuPDF4LLMLoader("data/papers/attention.pdf")
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)
chunks = splitter.split_documents(docs)  # split documents preserves the metadata
# in each document

embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

if not os.path.exists("data/chroma/attention_paper"):
    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory="data/chroma/attention_paper"
    )  # it performs the embedding directly here only
else:
    vectorstore = Chroma(
        persist_directory="data/chroma/attention_paper", embedding_function=embeddings
    )
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})  # it is a runnable, wow

prompt = ChatPromptTemplate.from_template(
    dedent("""
You are an expert research assistant. You need to answer the query based on the given context only.
Also, cite the page number when it is relevant and important to do so.
context: {context}
question: {question}
    """)
)
model = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()} | prompt | model | StrOutputParser()
)

rag_response1 = rag_chain.invoke("Explain multi-head attention in 2 sentences.")
print(rag_response1)

rag_response2 = rag_chain.invoke("What are the BLEU scores reported in the paper?")
print(rag_response2)

rag_response3 = rag_chain.invoke("Why is positional encoding needed?")
print(rag_response3)
