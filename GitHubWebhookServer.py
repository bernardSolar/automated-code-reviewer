from flask import Flask, request
import hmac
import hashlib
import json
import os
from anthropic import Anthropic

app = Flask(__name__)

# Webhook secret should be configured when setting up the webhook
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

@app.route('/webhook', methods=['POST'])
def webhook():
    # Verify webhook signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        return 'Invalid signature', 401

    # Parse the webhook payload
    event = request.headers.get('X-GitHub-Event')
    if event == 'push':
        payload = json.loads(request.data)
        
        # Get commit details
        commits = payload['commits']
        repo_name = payload['repository']['full_name']
        
        # Initialize Anthropic client
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Create message for Claude to analyze commits
        message = f"Please review these commits for repository {repo_name}:\n\n"
        for commit in commits:
            message += f"Commit: {commit['id']}\n"
            message += f"Author: {commit['author']['name']}\n"
            message += f"Message: {commit['message']}\n"
            message += f"Changes: {commit['url']}\n\n"
        
        # Send to Claude for analysis
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": message
            }]
        )
        
        # Store or forward Claude's analysis as needed
        print(f"Claude's analysis: {response.content}")
        
        return 'Webhook processed', 200

def verify_signature(payload, signature):
    if not signature or not WEBHOOK_SECRET:
        return False
    
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

if __name__ == '__main__':
    app.run(port=3000)
