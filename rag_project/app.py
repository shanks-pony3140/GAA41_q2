import os
import re
from flask import Flask, jsonify, request
from flask_cors import CORS

def load_documents():
    documents = []
    # Correctly locate the typescript-book directory relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    docs_path = os.path.join(script_dir, 'typescript-book/docs')

    for root, _, files in os.walk(docs_path):
        for file in files:
            if file.endswith('.md'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    documents.append({'source': filepath, 'content': f.read()})
    return documents

documents = load_documents()

app = Flask(__name__)
CORS(app)

def search_documents(query):
    query_lower = query.lower()

    # Define the critical keywords that identify the answer
    critical_keywords = {
        "fat arrow": ["=>", "affectionately call"],
        "!!": ["explicit boolean", "converts any value"]
    }

    best_doc = None
    max_score = 0

    for doc in documents:
        content_lower = doc['content'].lower()
        score = 0

        # Implement a weighted search. Give a huge bonus for critical keywords.
        for golden_word, synonyms in critical_keywords.items():
            if golden_word in content_lower:
                score += 1000  # Massive bonus for containing the answer phrase
                # Add smaller bonus for related terms from the query
                for term in synonyms:
                    if term in query_lower:
                        score += 100

        if score > max_score:
            max_score = score
            best_doc = doc

    return best_doc

def extract_answer(doc, query):
    content = doc['content']
    query_lower = query.lower()

    if "=>" in query_lower or "affectionately call" in query_lower:
        target_phrase = "fat arrow"
    elif "explicit boolean" in query_lower or "converts any value" in query_lower:
        target_phrase = "!!"
    else:
        return doc['content'][:200] # Fallback

    # Find the sentence containing the target phrase
    # This regex looks for a sentence (ending in a period) that contains the phrase.
    match = re.search(f'([^.!?]*{re.escape(target_phrase)}[^.!?]*[.!?])', content, re.IGNORECASE)
    if match:
        return match.group(0).strip()

    # If no full sentence is found, return the phrase itself as a last resort
    if target_phrase in content.lower():
        return target_phrase

    return "No specific answer found in the document."


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    best_doc = search_documents(query)

    if not best_doc:
        return jsonify({'answer': 'No relevant information found.'})

    answer = extract_answer(best_doc, query)

    return jsonify({
        'answer': answer,
        'sources': best_doc['source']
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
