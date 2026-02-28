"""Chat service for AI-powered conversations.

NOTE: This module previously created a RedisSession at import time with a hardcoded
session ID. This has been removed. Use practice_runner.get_session(session_id) 
to get a properly scoped session for each practice session.
"""
from mem0_setup import mem0_client

# Redis session creation removed - sessions should be created per-practice-session
# with dynamic session IDs. Use practice_runner.get_session(session_id) instead.