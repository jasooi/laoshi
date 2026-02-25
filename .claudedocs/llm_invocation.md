# Calling LLM API

## Invoking the API
- Use openai sdk to send requests to LLMs
- API keys are stored in .env, use Python's dotenv package to retrieve it
- ALWAYS validate the LLM's response against the expected JSON response schema - if output is malformed or not in the proper JSON format, retry the request
- you MUST set an iteration limit and retry timeout for each API
- Implement retry logic with exponential backoff
- Ensure errors are handled gracefully with user-friendly messages
- Implement logging for debugging API issues

