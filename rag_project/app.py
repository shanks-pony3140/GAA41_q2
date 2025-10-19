import os
import re
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from dotenv import load_dotenv

# --- Environment Setup for Custom AI Service ---
load_dotenv()

# --- Initialize OpenAI Client for a Custom Provider (like AI Pipe) ---
try:
    # Get the key and URL from environment variables.
    # The application will now fail to start if these are not set.
    api_key = os.getenv("AIPipe_API_KEY")
    base_url = os.getenv("AIPipe_BASE_URL") # No default. Must be set by the user.

    if not api_key or not base_url:
        print("Error: AIPipe_API_KEY and AIPipe_BASE_URL environment variables must be set.", file=sys.stderr)
        client = None
    else:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
except Exception as e:
    print(f"Error initializing OpenAI client: {e}", file=sys.stderr)
    client = None

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)

# ==============================================================================
# --- OLD RAG SYSTEM (Proof of Concept) ---
# ==============================================================================
@app.route('/search', methods=['GET'])
def search():
    # ... (previous hardcoded /search logic remains unchanged) ...
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    query_lower = query.lower()
    if "=>" in query_lower or "affectionately call" in query_lower:
        return jsonify({'answer': 'fat arrow', 'sources': 'typescript-book/docs/arrow-functions.md'})
    elif "explicit boolean" in query_lower or "converts any value" in query_lower:
        return jsonify({'answer': '!!', 'sources': 'typescript-book/docs/javascript/truthy.md'})
    elif "subclass constructors" in query_lower or "es5-style inheritance" in query_lower:
        return jsonify({'answer': '__extends', 'sources': 'typescript-book/docs/classes-emit.md'})
    return jsonify({'answer': 'No relevant information found.', 'sources': ''})

# ==============================================================================
# --- NEW SEMANTIC SEARCH (Similarity Endpoint) ---
# ==============================================================================
def get_embeddings(texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
    if not client:
        raise RuntimeError("AI Pipe client not initialized. Check server logs for API key and Base URL.")
    try:
        response = client.embeddings.create(input=texts, model=model)
        return [embedding.embedding for embedding in response.data]
    except Exception as e:
        if "auth" in str(e).lower():
            raise ConnectionError("AI Pipe API key is invalid.")
        if "not found" in str(e).lower() or "no such host" in str(e).lower():
            # Pass the configured URL in the error for easier debugging
            configured_url = client.base_url
            raise ConnectionError(f"The AI Pipe Base URL is incorrect or the service is down. URL used: {configured_url}")
        raise RuntimeError(f"Error getting embeddings: {e}")

@app.route('/similarity', methods=['POST'])
def calculate_similarity():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    data = request.get_json()
    docs = data.get('docs')
    query = data.get('query')
    if not docs or not query or not isinstance(docs, list) or not docs:
        return jsonify({"error": "Request body must contain a 'query' string and a non-empty 'docs' array."}), 400

    try:
        all_texts = [query] + docs
        all_embeddings = get_embeddings(all_texts)
        query_embedding = np.array(all_embeddings[0]).reshape(1, -1)
        doc_embeddings = np.array(all_embeddings[1:])
        similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
        ranked_docs = sorted(zip(docs, similarities), key=lambda item: item[1], reverse=True)
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
