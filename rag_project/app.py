import os
import re
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

# --- FIX: Initialize the Flask app BEFORE using it ---
app = Flask(__name__)
CORS(app)
# ----------------------------------------------------

def load_documents():
    documents = []
    # Correctly locate the typescript-book directory relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_path = os.path.join(script_dir, 'typescript-book/docs')

    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        documents.append({'source': filepath, 'content': f.read()})
                except Exception as e:
                    print(f"Error reading {filepath}: {e}", file=sys.stderr)
    return documents

documents = load_documents()

def search_documents(query):
    query_lower = query.lower()
    # Remove punctuation and split into keywords
    keywords = set(re.sub(r'[^\w\s]', '', query_lower).split())

    stopwords = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will', 'with', 'what', 'ts'}
    keywords = keywords - stopwords

    best_doc = None
    max_score = 0

    for doc in documents:
        content_lower = doc['content'].lower()
        score = 0

        # Score based on the number of unique query keywords found in the document
        unique_hits = sum(1 for keyword in keywords if keyword in content_lower)
        score = unique_hits

        if score > max_score:
            max_score = score
            best_doc = doc

    return best_doc

def extract_answer(doc, query):
    content = doc['content']
    query_lower = query.lower()
    keywords = set(re.sub(r'[^\w\s]', '', query_lower).split())
    stopwords = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will', 'with', 'what', 'ts'}
    keywords = keywords - stopwords

    # Split the document into sentences
    sentences = re.split(r'(?<=[.!?])\s+', content)

    best_sentence = ""
    max_score = 0

    for sentence in sentences:
        sentence_lower = sentence.lower()
        score = 0
        # Score sentences based on how many keywords they contain
        for keyword in keywords:
            if keyword in sentence_lower:
                score += 1

        if score > max_score:
            max_score = score
            best_sentence = sentence

    if best_sentence:
        return best_sentence.strip()

    # Fallback if no good sentence is found
    return content[:300] + "..."


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    best_doc = search_documents(query)

    if not best_doc:
        return jsonify({'answer': 'No relevant information found.', 'sources': ''})

    answer = extract_answer(best_doc, query)

    return jsonify({
        'answer': answer,
        'sources': best_doc['source']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
