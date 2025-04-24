import os
import asyncio
from google import genai
from dotenv import load_dotenv, find_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
)
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams,PointStruct
from google.genai import types
from langchain_text_splitters import (
    MarkdownTextSplitter,
   
)


# Load environment variables (only once)
load_dotenv(find_dotenv())

# Retrieve necessary environment variables
gemini_api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("MODEL_NAME")
base_url = os.getenv("LLM_BASE_URL")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "gemini-embeddings")
EMBED_MODEL = os.getenv("EMBED_MODEL", "models/embedding-001")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 800))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 160))


# Debug output to verify environment variables
# print(f"{gemini_api_key=}, {model_name=}, {base_url=}, {COLLECTION_NAME=}, {EMBED_MODEL=}, {CHUNK_SIZE=}, {CHUNK_OVERLAP=}, {QDRANT_URL=}, {QDRANT_API_KEY=}")

if not gemini_api_key or not model_name or not base_url:
    raise Exception("Gemini API key or credentials not found in .env file")

# Set up the Qdrant client

qdrant_client = QdrantClient(
    url=QDRANT_URL, 
    api_key=QDRANT_API_KEY,
)


# Create an instance of the external LLM client (Gemini)
client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url=base_url
)

# Set up the agents configuration
set_default_openai_client(client=client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)


embeddings = genai.Client(api_key=gemini_api_key)



async def create_collection():
    # Check if the collection already exists
    collections = qdrant_client.get_collections()
    collection_names = [collection.name for collection in collections.collections]
    if COLLECTION_NAME in collection_names:
        print(f"Collection '{COLLECTION_NAME}' already exists.")
        return

    # Create a new collection with the specified parameters
    qdrant_client.create_collection(
    collection_name=COLLECTION_NAME,
     vectors_config=VectorParams(size=768, distance=Distance.COSINE)
    )

    print(qdrant_client.get_collections())
    print(f"Collection '{COLLECTION_NAME}' created successfully.")

async def create_embeddings():
   with open("comprehensive_guide_daca.md","r",encoding="utf-8") as f:
       markdown_text= f.read()
       splitter = MarkdownTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
       chunks = splitter.split_text(markdown_text)
       print(f"Number of chunks: {len(chunks)}")

       result = embeddings.models.embed_content(
        model=EMBED_MODEL,
         contents=chunks,
        config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")
        )

       print(result.embeddings)
       points = []
       for index, chunk in enumerate(chunks):
   
        embedding_obj = result.embeddings[index]
        raw_vector = embedding_obj.values
        points.append(
            PointStruct(
                id=index+97,
                vector=raw_vector,
                payload={"text": chunk}
            )
        )         
        # print(f"Chunk {index}: {chunk}")
        # print(f"Embedding {index}: {result.embeddings}")
        # print(points)
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
       print(f"Upserted {len(points)} points to Qdrant collection '{COLLECTION_NAME}'.")
       print(f"Number of points in collection '{COLLECTION_NAME}': {qdrant_client.count(collection_name=COLLECTION_NAME)}")
         
# asyncio.run(create_collection())
# asyncio.run(create_embeddings())

@function_tool
def qdrant_search(query:str,top_k:int=5):
    """  
    This tool is designed to be used for searching about all questions.
    It searches the Information in Qdrant collection for the most relevant documents based on the provided query.
    To perform a search in Qdrant using the provided query and return the top_k results.
  
    Args:
        query (str): The query string to search for.
        top_k (int): The number of top results to return.
    """
    # Embed the user query and extract vector
    query_resp = embeddings.models.embed_content(
        model=EMBED_MODEL,
        contents=query,
               config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY")

    )
    q_emb = query_resp.embeddings[0].values

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=q_emb,
        limit=top_k
    )
    # Return the raw text of top hits
    # print(f"Query: {query}")
    # print(f"Results: {results}")
    return results
    

# Create the talking agent instance
talking_agent = Agent(
    name="DACA Assistant",
    instructions="You are a DACA Assistant you all info in this rag system of tools, it have all information, you first look info in tools, if it has so give simplified answer according to knowlegebase",
    model=model_name,
    tools=[qdrant_search]
)

async def main(query: str | list[dict[str, str]]):
    res = await Runner.run(talking_agent, input=query)
    print(f"Response: {res.final_output}")
    return res.final_output 

if __name__ == "__main__":
    input_text = input("Enter your query: ")
    asyncio.run(main(input_text))
