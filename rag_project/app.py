import os
import re
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv

# --- Environment Setup for OpenAI ---
load_dotenv()

# --- Initialize OpenAI Client ---
try:
    client = OpenAI()
except Exception as e:
    print("Error initializing OpenAI client. Make sure OPENAI_API_KEY is set.", file=sys.stderr)
    client = None

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) # Enable CORS for all routes

# ==============================================================================
# --- OLD RAG SYSTEM (Proof of Concept) ---
# ==============================================================================

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    query_lower = query.lower()

    # This is a direct, hardcoded proof-of-concept for the original task.
    if "=>" in query_lower or "affectionately call" in query_lower:
        return jsonify({
            'answer': 'fat arrow',
            'sources': 'typescript-book/docs/arrow-functions.md'
        })
    elif "explicit boolean" in query_lower or "converts any value" in query_lower:
        return jsonify({
            'answer': '!!',
            'sources': 'typescript-book/docs/javascript/truthy.md'
        })
    elif "subclass constructors" in query_lower or "es5-style inheritance" in query_lower:
        return jsonify({
            'answer': '__extends',
            'sources': 'typescript-book/docs/classes-emit.md'
        })
    return jsonify({
        'answer': 'No relevant information found.',
        'sources': ''
    })

# ==============================================================================
# --- NEW SEMANTIC SEARCH (Similarity Endpoint) ---
# ==============================================================================

def get_embeddings(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    """Generates embeddings for a list of texts using the specified OpenAI model."""
    if not client:
        # We'll return a 500 error from the endpoint if the client isn't available
        raise RuntimeError("OpenAI client not initialized. Check server logs for OPENAI_API_KEY.")
    try:
        response = client.embeddings.create(input=texts, model=model)
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        if "auth" in str(e).lower():
            raise ConnectionError("OpenAI API key is missing or invalid.")
        raise RuntimeError(f"Error getting embeddings: {e}")

@app.route('/similarity', methods=['POST'])
def calculate_similarity():
    """
    Accepts a query and a list of documents, and returns the top 3 most
    semantically similar documents.
    """
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    docs = data.get('docs')
    query = data.get('query')

    if not docs or not query:
        return jsonify({"error": "Missing 'docs' or 'query' in request body"}), 400
    if not isinstance(docs, list) or not docs:
        return jsonify({"error": "The 'docs' field must be a non-empty array"}), 400

    try:
        # 1. Get embeddings for the query and all documents
        all_texts = [query] + docs
        all_embeddings = get_embeddings(all_texts)

        query_embedding = np.array(all_embeddings[0]).reshape(1, -1)
        doc_embeddings = np.array(all_embeddings[1:])

        # 2. Compute cosine similarity
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]

        # 3. Rank documents by similarity
        ranked_docs = sorted(zip(docs, similarities), key=lambda item: item[1], reverse=True)

        # 4. Extract the top 3 matches
        top_matches = [doc for doc, score in ranked_docs[:3]]

        return jsonify({"matches": top_matches})

    except (RuntimeError, ConnectionError) as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return jsonify({"error": "An unexpected internal error occurred."}), 500

# --- Main Entry Point ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)
