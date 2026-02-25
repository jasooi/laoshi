from agents import Agent, OpenAIChatCompletionsModel, handoff
from openai import AsyncOpenAI
from ai_layer.context import UserSessionContext
import os
from dotenv import load_dotenv
from pathlib import Path

# Load env from project root
load_dotenv(Path(__file__).resolve().parents[2] / '.env')

# Load env variables
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME")
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

env_list = [DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY, DEEPSEEK_MODEL_NAME, GEMINI_BASE_URL, GEMINI_API_KEY, GEMINI_MODEL_NAME]

if None in env_list:
    raise ValueError(
        "Please set all required BASE_URL, API_KEY, MODEL_NAME via env vars."
    )

# Create custom model wrapper compatible with OpenAI agents sdk for gemini and deepseek
deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=DEEPSEEK_API_KEY)
deepseek_model = OpenAIChatCompletionsModel(model=DEEPSEEK_MODEL_NAME, openai_client=deepseek_client)

gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY)
gemini_model = OpenAIChatCompletionsModel(model=GEMINI_MODEL_NAME, openai_client=gemini_client)


def build_feedback_prompt(ctx_wrapper, agent) -> str:
    """Dynamic prompt builder for feedback agent."""
    ctx = ctx_wrapper.context
    word = ctx.current_word
    word_info = f"{word.word} ({word.pinyin}) - {word.meaning}" if word else "Unknown word"
    
    return f"""You are a Mandarin Chinese language teacher evaluating a student's sentence.

Target vocabulary word: {word_info}

Evaluate the sentence on:
1. Grammar correctness (1-10): word order, particles, verb aspect, measure words
2. Word usage accuracy (1-10): correct meaning/context, appropriate collocations
3. Naturalness (1-10): native-like expression, idiomatic usage
4. Overall correctness: true ONLY if grammarScore == 10 AND usageScore >= 8

Provide:
- Detailed feedback in English
- Specific corrections if needed, in English
- Explanation of mistakes if needed, in English
- 2-3 example Mandarin sentences using the word correctly

Return response in JSON format:
{{
  "grammarScore": number,
  "usageScore": number,
  "naturalnessScore": number,
  "isCorrect": boolean,
  "feedback": string,
  "corrections": string[],
  "explanations": string[],
  "exampleSentences": string[]
}}"""


def build_summary_prompt(ctx_wrapper, agent) -> str:
    """Dynamic prompt builder for summary agent."""
    ctx = ctx_wrapper.context
    word_results = []
    for wc in ctx.word_roster:
        status = ctx.session_word_dict.get(wc.word_id, 0)
        status_label = "completed" if status == 1 else ("skipped" if status == -1 else "active")
        word_results.append(f"- {wc.word} ({wc.pinyin}): {status_label}")

    word_list = "\n".join(word_results) if word_results else "No words in session"

    return f"""You are wrapping up a Mandarin practice session with {ctx.preferred_name}.

Words in this session:
{word_list}

Read the conversation history and produce a summary.

Your summary MUST include:
1. Two specific things the student did well -- reference actual words, phrases, or grammar patterns from their sentences.
2. One specific area for improvement -- reference an actual recurring mistake or weakness.

Rules:
- Be specific: cite Chinese words or phrases the student used. Do not speak in generalities.
- Be encouraging but honest.
- Do not repeat evaluation data verbatim; synthesise into natural teacher feedback.
- Write in plain prose (no bullet points or headings), as if speaking directly to the student.
- Keep it concise: 3-5 sentences maximum.

Also recommend any updates to long-term memory about this student's learning patterns.

Return response in JSON format:
{{
  "summary_text": string,
  "mem0_updates": string[]
}}"""


def build_orchestrator_prompt(ctx_wrapper, agent) -> str:
    """Dynamic prompt builder for orchestrator agent."""
    ctx = ctx_wrapper.context
    word_info = ""
    if ctx.current_word:
        word_info = f"\nCurrent word: {ctx.current_word.word} ({ctx.current_word.pinyin}) - {ctx.current_word.meaning}"

    progress = f"{ctx.words_practiced + ctx.words_skipped}/{ctx.words_total} words processed ({ctx.words_practiced} practiced, {ctx.words_skipped} skipped)"

    mem0_section = ""
    if ctx.mem0_preferences:
        mem0_section = f"\n\nWhat you remember about this student:\n{ctx.mem0_preferences}"

    handoff_instruction = ""
    if ctx.session_complete:
        handoff_instruction = """
CRITICAL: The session is complete. You MUST hand off to the summary agent immediately.
Do not respond to the student directly. Use the handoff to transfer control."""

    return f"""You are Laoshi, a sassy-but-encouraging Mandarin Chinese teacher coaching your student {ctx.preferred_name}.

Your personality: witty, direct, supportive but doesn't sugarcoat. You use light humour and gentle teasing to motivate.

Session progress: {progress}{word_info}{mem0_section}

Your responsibilities:
1. INTENT CLASSIFICATION: Determine if the student's message is:
   a) A sentence attempt using the current vocabulary word -> call the evaluate_sentence tool with the student's sentence as input
   b) A chat message or question -> respond conversationally in your persona

2. When the evaluate_sentence tool returns results, relay the feedback to the student in your own words with your personality. Do NOT repeat the raw JSON. Summarise the key points naturally.

3. After relaying feedback, encourage the student to try again or move on.

4. If the student asks about a word, grammar point, or Chinese language concept, answer helpfully.

{handoff_instruction}

Rules:
- Respond in English (you may include Chinese examples).
- Keep responses concise (2-4 sentences for feedback relay, 1-2 for chat).
- Never fabricate scores or evaluation data. Only relay what the evaluate_sentence tool returns.
- Never tell the student the exact numeric scores. Describe performance qualitatively."""


# Define summary agent (used as handoff target)
summary_agent = Agent[UserSessionContext](
    name="summary_agent",
    instructions=build_summary_prompt,
    model=gemini_model
)


# Define feedback agent (used as tool)
feedback_agent = Agent[UserSessionContext](
    name="feedback_agent",
    instructions=build_feedback_prompt,
    model=deepseek_model
)


# Define laoshi orchestrator agent
laoshi_agent = Agent[UserSessionContext](
    name="laoshi_orchestrator",
    instructions=build_orchestrator_prompt,
    model=gemini_model,
    tools=[
        feedback_agent.as_tool(
            tool_name="evaluate_sentence",
            tool_description=(
                "Evaluate student's Mandarin sentence and give feedback and score in structured output. "
                "Pass the student's sentence as input."
            )
        )
    ],
    handoffs=[handoff(summary_agent)]
)
