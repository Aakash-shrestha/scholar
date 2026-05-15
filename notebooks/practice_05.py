from langchain_community.document_loaders import PyMuPDFLoader

loader = PyMuPDFLoader("data/papers/attetion_is_all_you_need.pdf")
docs = loader.load()

print(len(docs))
print(docs[0].metadata)
print(docs[0].page_content)
