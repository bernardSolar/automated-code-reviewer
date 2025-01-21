from flask import Flask, request
import hmac
import hashlib
import json
import os
from anthropic import Anthropic
from github import Github
import re
import difflib

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')

class RefactoringAnalyzer:
    def __init__(self, github_client):
        self.gh = github_client
        self.patterns = {
            'static_to_instance': {
                'pattern': r'static\s+\w+',
                'message': 'Converting static variables to instance variables'
            },
            'new_class': {
                'pattern': r'class\s+\w+',
                'message': 'Extracting new class'
            },
            'interface': {
                'pattern': r'interface\s+\w+',
                'message': 'Creating interface for better abstraction'
            },
            'dependency_injection': {
                'pattern': r'@Inject|@Autowired|\w+\([^)]*\)\s*{',
                'message': 'Implementing dependency injection'
            }
        }

    def analyze_diff(self, diff_text):
        findings = []
        
        # Look for specific refactoring patterns
        for name, pattern in self.patterns.items():
            if re.search(pattern['pattern'], diff_text):
                findings.append({
                    'type': name,
                    'message': pattern['message']
                })
        
        # Additional analysis for code smells being fixed
        if 'private static' in diff_text and 'private final' in diff_text:
            findings.append({
                'type': 'encapsulation',
                'message': 'Improving encapsulation by making fields private and final'
            })
            
        return findings

    def create_review_comment(self, repo, commit_sha, findings):
        # Create a detailed comment
        comment = "## Refactoring Analysis 🔍\n\n"
        
        if findings:
            comment += "Found the following refactoring patterns:\n\n"
            for finding in findings:
                comment += f"- **{finding['type']}**: {finding['message']}\n"
        else:
            comment += "No major refactoring patterns detected in this commit.\n"
        
        # Add suggestions if needed
        if any(f['type'] == 'static_to_instance' for f in findings):
            comment += "\n### Suggestion 💡\n"
            comment += "Consider extracting these instance variables into a new class "
            comment += "to better represent the domain model.\n"
        
        # Create commit comment
        repo.get_commit(commit_sha).create_comment(comment)

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
        
        # Initialize clients
        gh = Github(GITHUB_TOKEN)
        anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
        analyzer = RefactoringAnalyzer(gh)
        
        repo_name = payload['repository']['full_name']
        repo = gh.get_repo(repo_name)
        
        for commit in payload['commits']:
            # Get the commit diff
            commit_obj = repo.get_commit(commit['id'])
            diff = commit_obj.get_combined_status()
            
            # Analyze the changes
            findings = analyzer.analyze_diff(diff)
            
            # Create a message for Claude to analyze
            message = f"""Please analyze this commit for refactoring patterns:
            
            Commit: {commit['id']}
            Author: {commit['author']['name']}
            Message: {commit['message']}
            
            Findings from automated analysis:
            {json.dumps(findings, indent=2)}
            
            Diff:
            {diff}
            
            Please provide:
            1. Your assessment of the refactoring approach
            2. Suggestions for next steps
            3. Any potential issues or code smells that should be addressed
            """
            
            # Get Claude's analysis
            response = anthropic.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": message
                }]
            )
            
            # Create a combined review comment
            full_comment = f"""## Refactoring Review 🔄

### Automated Analysis
{analyzer.create_review_comment(repo, commit['id'], findings)}

### Claude's Analysis
{response.content}

### Next Steps 🚀
Would you like me to:
- Create detailed issue tickets for any suggested improvements?
- Provide example code snippets for alternative approaches?
- Analyze test coverage for the modified code?

Just add a comment with your preference!
"""
            
            # Post the comment
            commit_obj.create_comment(full_comment)
            
        return 'Analysis complete', 200

    return 'Event not processed', 200

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
