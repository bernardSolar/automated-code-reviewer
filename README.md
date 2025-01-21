# Automated Code Reviewer

An automated code review system that provides immediate feedback on commits using pattern matching and AI analysis.

See [DOCUMENTATION.md](DOCUMENTATION.md) for full details.

## Quick Start

1. Clone the repository
2. Set up environment variables
3. Configure webhook in your target repository
4. Run the server

## Requirements

- Python 3.8+
- GitHub account
- Anthropic API key

## Environment Variables

```bash
WEBHOOK_SECRET=your_webhook_secret
ANTHROPIC_API_KEY=your_anthropic_key
GITHUB_TOKEN=your_github_token
```

## Running the Server

```bash
python main.py
```