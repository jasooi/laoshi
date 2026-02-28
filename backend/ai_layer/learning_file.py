# DO NOT use this file! This is a test script.
# This file contains all function tool definitions for LLMs to use
from mem0 import MemoryClient
from agents.extensions.memory import SQLAlchemySession
from agents import (
    Agent,
    Runner,
    function_tool,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_disabled,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    ModelSettings,
    SQLiteSession
)
import random
from dataclasses import dataclass
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')

import json

# Load env variables
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL") or ""
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or ""
DEEPSEEK_MODEL_NAME = os.getenv("DEEPSEEK_MODEL_NAME") or ""

if not DEEPSEEK_BASE_URL or not DEEPSEEK_API_KEY or not DEEPSEEK_MODEL_NAME:
    raise ValueError(
        "Please set EXAMPLE_BASE_URL, EXAMPLE_API_KEY, EXAMPLE_MODEL_NAME via env var or code."
    )


GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL") or ""
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or ""
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME") or ""

if not GEMINI_BASE_URL or not GEMINI_API_KEY or not GEMINI_MODEL_NAME:
    raise ValueError(
        "Please set EXAMPLE_BASE_URL, EXAMPLE_API_KEY, EXAMPLE_MODEL_NAME via env var or code."
    )


# create local context object for OpenAI agents
@dataclass
class UserSessionContext:
    user_id: int
    session_id: int

# Configure settings to use non-OpenAI model as main model: without OpenAI API key you need this
client = AsyncOpenAI(
    base_url=DEEPSEEK_BASE_URL,
    api_key=DEEPSEEK_API_KEY,
)
# set_default_openai_client(client=client, use_for_tracing=False)
# set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)

deepseek_client = AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=DEEPSEEK_API_KEY)
deepseek_model = OpenAIChatCompletionsModel(model=DEEPSEEK_MODEL_NAME, openai_client=deepseek_client)

gemini_client = AsyncOpenAI(base_url=GEMINI_BASE_URL, api_key=GEMINI_API_KEY)
gemini_model = OpenAIChatCompletionsModel(model="gemini-2.5-flash", openai_client=gemini_client)

settings = ModelSettings(
    model=DEEPSEEK_MODEL_NAME,
    truncation="disabled"
)



# define regular function
@function_tool
def give_next_word(wrapper: RunContextWrapper[UserSessionContext]) -> str:
    """This tool returns a random English word from a list of words. 
    Call this function to give the learner a new English word to study."""
    word_list = [
        "imperceptible", 
        "irrevocable", 
        "preposterous", 
        "valiant", 
        "recalcitrant"
        ]
    picked_word= word_list[random.randint(0, len(word_list)-1)]
    return picked_word


# -------start mem0 service------------
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# customise memory creation and update instructions
mem0_client.project.update(custom_instructions="""
Extract and remember:
- Language learning topics mentioned
- Current skill level for each topic
- Learning goals and deadlines
- Progress updates and completions
- Preferred learning method (example sentences, sentence construction exercises)

Do not store:
- Personal identifiers beyond the user_id
- Payment or financial information
- Off-topic conversation that isn't about learning
""")

# Add custom categories for mem0 memory file
mem0_client.project.update(custom_categories=[
	{"name": "weak_points", "description": "areas of weaknesses of the user in language learning"},
	{"name": "skill_levels", "description": "Proficiency: beginner, intermediate, advanced"},
	{"name": "learning_goals", "description": "Learning objectives and targets"},
	{"name": "personal_information", "description": "Basic information about the user including name, hobbies and personality traits"},
	{"name": "preferences", "description": "Learning style, schedule, or feedback format preferences"}
])


# define mem0-access function tools for the agent
@function_tool
def search_memory(
    ctx: RunContextWrapper[UserSessionContext],
    query: str,
    category: str = None
) -> str:
    """Search user's learner profile and personality. Optionally filter by category."""
    filters = {"user_id": ctx.context.user_id}
    if category:
        filters["categories"] = {"contains": category}

    memories = mem0_client.search(query, filters=filters, limit=5)
    if memories and memories.get("results"):
        return "\n".join([
            f"- [ID: {m['id']}] {m['memory']}" for m in memories["results"]
        ])
    return "No relevant memories found."


@function_tool
def save_memory(ctx: RunContextWrapper[UserSessionContext], content: str) -> str:
    """Save new information about the user's learning journey."""
    mem0_client.add(
        [{"role": "user", "content": content}],
        user_id=ctx.context.user_id,
        session_id=ctx.context.session_id
    )
    return "Memory saved successfully."

@function_tool
def update_memory(ctx: RunContextWrapper[UserSessionContext], memory_id: str, new_text: str) -> str:
    """Update an existing memory with new information."""
    mem0_client.update(memory_id=memory_id, text=new_text)
    return f"Memory {memory_id} updated."

@function_tool
def delete_memory(ctx: RunContextWrapper[UserSessionContext], memory_id: str) -> str:
	"""Delete a specific memory by ID if the memory is no longer valid or correct."""
	mem0_client.delete(memory_id=memory_id)
	return f"Memory {memory_id} deleted."


# define instructions dynamically
def build_system_prompt(
    context: RunContextWrapper[UserSessionContext],
    agent: Agent[UserSessionContext]
) -> str:
    return f"""You are a friendly english teacher helping student with ID number {context.context.user_id} to practice their English.
    Greet them with their ID number first.

    Use search_memory to recall what the user is learning and their level.
    Search results include memory IDs in format [ID: xxx].
    Use save_memory to store new topics, preferences, or progress.
    Use update_memory when information changes. First search to find the memory ID, then call update_memory with that ID and the new text.
    Always check memory before responding to personalize your answers.

    Answer your student's questions in a friendly way.
    Use the give_next_word tool to assign a new word for the student to study, if you think the student is ready for it."""
    


# define agent
friendly_teacher_agent = Agent[UserSessionContext](
    name="friendly-teacher",
    instructions= build_system_prompt,
    model=gemini_model,
    tools=[
        give_next_word,
        search_memory,
        save_memory,
        update_memory,
        delete_memory
        ]
)

def get_model_output(result):
    full_text = ""
    for response in result.raw_responses:
        for item in response.output:
            if hasattr(item, 'content'):  # it's a message, not a tool call
                for block in item.content:
                    if hasattr(block, 'text'):
                        full_text += block.text + "\n"
    return full_text.strip()



async def main():
    user_id = input("What is your user_id?")
    session_id = input("What is the session_id?")
    context_var = UserSessionContext(user_id=user_id, session_id=session_id)

    # then start session for agent run --> Create a session instance with a session ID
    session = SQLiteSession(session_id)

    user_question = input("Ask teacher a question:\n")

    result = await Runner.run(friendly_teacher_agent, input=user_question, context=context_var, session=session)
    print(f"{get_model_output(result)}\n")

    while 1:
        user_response = input("Type here: ")
        if user_response.lower() == "exit":
            print("Conversation ended\n")
            break

        if "print_memory" in user_response:
            memory = mem0_client.get_all(filters={"user_id":"*"}, page=1, page_size=20)
            print(json.dumps(memory, indent=4))
            continue

        result = await Runner.run(friendly_teacher_agent, input=user_response, context=context_var, session=session)
        print(f"{get_model_output(result)}\n")




if __name__ == "__main__":
    asyncio.run(main())