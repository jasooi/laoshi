# DO NOT use this file! It is archived for now

from mem0_setup import mem0_client
from agents import Agent, Runner, function_tool, RunContextWrapper
from context import UserSessionContext


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



# app db functions
@function_tool
def get_recent_sessions(user_id: int, last_n: int) -> list[]:
    """Queries the app database to retrieve the last N session 
    details of the user with user_id.
    Output: list of session details (session_start_timestamp, ...)"""

@function_tool
def get_session_words(session_id: int) -> list[]:
    """Queries the app database to retrieve the words practiced in
    the session with session_id.
    Output: list of words and corresponding session data (...)"""


@function_tool
def get_recent_mistakes(session_id: int) -> list[]:
    """Queries the app database to retrieve the words practiced in
    the session with session_id.
    Output: list of words and corresponding session data (...)"""


@function_tool
def get_session_words(session_id: int) -> list[]:
    """Queries the app database to retrieve the words practiced in
    the session with session_id.
    Output: list of words and corresponding session data (...)"""
    
    