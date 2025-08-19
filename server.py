import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import glob # Import the glob module to find files

# Initialize the Flask app
app = Flask(__name__)
# Enable CORS to allow requests from your frontend
CORS(app)

NERDGRAPH_URL = 'https://api.newrelic.com/graphql'

# --- Helper function to find the HTML file ---
def find_html_file():
    """Scans the current directory for the first file ending in .html."""
    html_files = glob.glob('*.html')
    if html_files:
        print(f"Found HTML file: {html_files[0]}")
        return html_files[0]
    print("ERROR: No .html file found in the current directory.")
    return None

# Store the HTML filename when the server starts
HTML_FILE = find_html_file()

# --- Route to serve the HTML file ---
@app.route('/')
@app.route('/index')
@app.route('/index.html')
def serve_index():
    """
    This endpoint serves the main HTML user interface.
    It looks for an HTML file in the same directory.
    """
    print("Request for root URL received.")
    if HTML_FILE:
        print(f"Serving HTML page: {HTML_FILE}")
        return send_from_directory('.', HTML_FILE)
    return "<h1>Error: No HTML file found</h1><p>Please make sure your HTML file is in the same directory as the server.py script.</p>", 404

# --- Route for general NRQL queries ---
@app.route('/query', methods=['POST'])
def handle_query():
    """
    This endpoint receives a NRQL query from the frontend, adds the secret API key,
    and forwards it to the New Relic NerdGraph API.
    """
    client_data = request.json
    api_key = client_data.get('apiKey')
    if not api_key:
        return jsonify({"error": "API Key is missing in the request from the client."}), 400

    print(f"Received NRQL query for Account ID: {client_data.get('variables', {}).get('accountId')}")
    
    graphql_payload = {
        "query": client_data.get('query'),
        "variables": client_data.get('variables')
    }

    return forward_to_nerdgraph(graphql_payload, api_key)

# --- Route for fetching entity details ---
@app.route('/entity', methods=['POST'])
def handle_entity_query():
    """
    This endpoint receives an entity GUID and fetches its details.
    """
    client_data = request.json
    api_key = client_data.get('apiKey')
    guid = client_data.get('guid')

    if not api_key:
        return jsonify({"error": "API Key is missing in the request from the client."}), 400
    if not guid:
        return jsonify({"error": "Entity GUID is required."}), 400
    
    print(f"Received entity details request for GUID: {guid}")

    graphql_payload = {
        "query": """
            query($guid: EntityGuid!) {
              actor {
                entity(guid: $guid) {
                  ... on Entity {
                    name
                    domain
                    type
                    guid
                    entityType
                    account {
                      id
                      name
                    }
                  }
                }
              }
            }
        """,
        "variables": { "guid": guid }
    }
    
    return forward_to_nerdgraph(graphql_payload, api_key)


def forward_to_nerdgraph(payload, api_key):
    """A helper function to forward a GraphQL payload to New Relic."""
    headers = {
        'Content-Type': 'application/json',
        'API-Key': api_key
    }
    try:
        response = requests.post(NERDGRAPH_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        print("Successfully fetched data from New Relic.")
        return jsonify(response.json())
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
        return jsonify({
            "error": f"New Relic API returned an error: {response.status_code}",
            "details": response.text
        }), response.status_code
    except requests.exceptions.RequestException as err:
        print(f"A network error occurred: {err}")
        return jsonify({"error": "A network error occurred while contacting the New Relic API."}), 503
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An unexpected server error occurred."}), 500

if __name__ == '__main__':
    # Run the app on port 5001 to avoid conflicts with other services
    app.run(port=5001, debug=True)
