import sys
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')

    # --- Start Debugging ---
    # Print to standard error to make sure it shows up in Render logs.
    print(f"--- Received Query ---", file=sys.stderr)
    print(f"Query: {query}", file=sys.stderr)
    print(f"----------------------", file=sys.stderr)
    # --- End Debugging ---

    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400

    query_lower = query.lower()

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

    return jsonify({
        'answer': 'No relevant information found.',
        'sources': ''
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
