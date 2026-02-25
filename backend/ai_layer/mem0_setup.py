# This file contains all function tool definitions for LLMs to use
from mem0 import MemoryClient
from dotenv import load_dotenv
import os
load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')


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

# Add custom categories for the mem0 memory store
mem0_client.project.update(custom_categories=[
	{"name": "weak_points", "description": "areas of weaknesses of the user in language learning"},
	{"name": "skill_levels", "description": "Proficiency: beginner, intermediate, advanced"},
	{"name": "learning_goals", "description": "Learning objectives and targets"},
	{"name": "personal_information", "description": "Basic information about the user including name, hobbies and personality traits"},
	{"name": "preferences", "description": "Learning style, schedule, or feedback format preferences"}
])



