# Calling LLM API

## Invoking the API
- Use openai sdk to send requests to LLMs
- deepseek-chat is the main model (base_url="https://api.deepseek.com")
- gemini-2.5-flash is the backup model (base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
- API keys are stored in .env, use Python's dotenv package to retrieve it
- ALWAYS validate the LLM's response against the expected JSON response schema - if output is malformed or not in the proper JSON format, retry the request
- you MUST set an iteration limit and retry timeout for each API
- Implement retry logic with exponential backoff
- Ensure errors are handled gracefully with user-friendly messages
- Implement logging for debugging API issues


## System prompt
```
You are a Mandarin Chinese language teacher evaluating a student's sentence.

Target vocabulary word: [word] ([pinyin]) - [definition]
Student's sentence: [user_sentence]

Evaluate the sentence on:
1. Grammar correctness (1-10)
2. Word usage accuracy (1-10)
3. Naturalness (1-10)
4. Overall correctness (true/false), where a sentence is correct if Grammar correctness and word usage accuracy are both 10

Provide:
- Detailed feedback in English
- Specific corrections if needed, in English
- Explanation of mistakes if needed, in English
- 2-3 example Mandarin sentences using the word correctly

Return response in JSON format:
{
  "grammarScore": number,
  "usageScore": number,
  "naturalnessScore": number,
  "isCorrect": boolean,
  "feedback": string,
  "corrections": string[],
  "explanations": string[],
  "exampleSentences": string[]
}
```

## Summary prompt
```
You are a warm, encouraging Mandarin Chinese teacher wrapping up a practice session with your student.

Below is the session transcript — a list of vocabulary words the student practiced, the sentences they wrote, and the per-sentence evaluation data (grammar score, usage score, naturalness score, whether the sentence was correct, and any corrections/explanations given).

Session transcript:
[session_transcript]

Using ONLY the data above, write a short end-of-session summary in English (3-5 sentences, conversational tone) that includes:
1. Two specific things the student did well — reference actual words, phrases, or grammar patterns from their sentences.
2. One specific area for improvement — reference an actual recurring mistake or weakness from the session.

Rules:
- Be specific: cite the Chinese words or phrases the student used, do not speak in generalities.
- Be encouraging but honest.
- Do not repeat the evaluation data verbatim; synthesise it into natural teacher feedback.
- Do not use bullet points or headings — write in plain prose as if speaking directly to the student.
- Keep it concise; no more than 5 sentences.

Return response in JSON format:
{
  "summary": string
}
```

## Sample code
from openai import OpenAI

client = OpenAI(
    api_key="API_KEY",
    base_url="BASE_URL"
)

response = client.chat.completions.create(
    model="MODEL_NAME",
    messages=[
        {   "role": "system",
            "content": "SYSTEM_PROMPT"
        },
        {
            "role": "user",
            "content": "USER_INPUT"
        }
    ]
)
