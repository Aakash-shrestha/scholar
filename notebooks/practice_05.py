from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

loader = PyMuPDF4LLMLoader("data/papers/attention.pdf")
docs = loader.load()

print(len(docs))
print(docs[0].metadata)
print(docs[0].page_content)


splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
)
chunks = splitter.split_documents(docs)  # split documents preserves the metadata
# in each document

print(len(chunks))
if chunks:
    print("first chunk:\n")
    print(chunks[0])
    print("chunk page content:\n")
    for chunk in chunks[0:5]:
        print(len(chunk.page_content))


#find the lenght of chunks containing multi-head in its content
matching = [c for c in chunks if "multi-head" in c.page_content.lower()]
print(f"found {len(matching)} chunks containing multi-head attention")
print(matching[0].page_content[:500])
print(matching[0].metadata)

#print equations
for c in chunks:
    if "softmax" in c.page_content.lower():
        print("softmax")
        print(c.page_content[:500])
        print("---")
        break

#print tables
for c in chunks:
    if "BLEU" in c.page_content.lower():
        print("bleu")
        print(c.page_content[:500])
        print("---")
        break
