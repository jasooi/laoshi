from mem0_setup import mem0_client
import redis
from agents.extensions.memory import RedisSession
from dotenv import load_dotenv
import os
load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')



session = RedisSession.from_url(
    "user_123",
    url=os.getenv("REDIS_URI"),
)