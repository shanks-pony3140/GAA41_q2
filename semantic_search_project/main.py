import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv

# --- Environment Setup ---
# For local development, create a .env file in this directory and add:
# OPENAI_API_KEY="your_api_key_here"
load_dotenv()

# --- Initialize OpenAI Client ---
# The client will automatically look for the OPENAI_API_KEY environment variable.
try:
    client = OpenAI()
except Exception as e:
    print("Error initializing OpenAI client. Make sure the OPENAI_API_KEY is set.")
    print(e)
    client = None

# --- FastAPI App Initialization ---
app = FastAPI()

# --- CORS Configuration ---
# Allow requests from all origins, with all methods and headers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods, including POST and OPTIONS
    allow_headers=["*"],
)

# --- Pydantic Models for Request/Response ---
class SimilarityRequest(BaseModel):
    docs: List[str]
    query: str

class SimilarityResponse(BaseModel):
    matches: List[str]

# --- Helper Function for Embeddings ---
def get_embeddings(texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
    """Generates embeddings for a list of texts using the specified OpenAI model."""
    if not client:
        raise HTTPException(status_code=500, detail="OpenAI client not initialized. Check server logs.")
    try:
        response = client.embeddings.create(input=texts, model=model)
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        # Provide a more specific error message if the API key is missing
        if "auth" in str(e).lower():
            raise HTTPException(status_code=401, detail="OpenAI API key is missing or invalid.")
        raise HTTPException(status_code=500, detail=f"Error getting embeddings: {e}")

# --- API Endpoint ---
@app.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: SimilarityRequest):
    """
    Accepts a query and a list of documents, and returns the top 3 most
    semantically similar documents.
    """
    if not request.docs:
        raise HTTPException(status_code=400, detail="The 'docs' array cannot be empty.")

    # 1. Get embeddings for the query and all documents in a single API call
    all_texts = [request.query] + request.docs
    all_embeddings = get_embeddings(all_texts)

    query_embedding = np.array(all_embeddings[0]).reshape(1, -1)
    doc_embeddings = np.array(all_embeddings[1:])

    # 2. Compute cosine similarity
    similarities = cosine_similarity(query_embedding, doc_embeddings)[0]

    # 3. Rank documents by similarity
    # Create a list of (document_text, similarity_score) tuples
    ranked_docs = sorted(zip(request.docs, similarities), key=lambda item: item[1], reverse=True)

    # 4. Extract the top 3 matches
    top_matches = [doc for doc, score in ranked_docs[:3]]

    return SimilarityResponse(matches=top_matches)

# --- Root Endpoint for Health Check ---
@app.get("/")
def read_root():
    return {"status": "Semantic Search API is running."}

# To run this application:
# 1. Make sure you have an OpenAI API key.
# 2. Create a file named `.env` in this directory.
# 3. Add `OPENAI_API_KEY="your_key_here"` to the .env file.
# 4. Install dependencies: pip install -r requirements.txt
# 5. Run the server: uvicorn main:app --reload
#
# The API will be available at http://127.0.0.1:8000
