# This file stores the configs for the Flask app
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')

class Config():
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
    SQL_ALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG=True