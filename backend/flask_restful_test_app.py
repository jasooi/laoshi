from flask import Flask, request
from flask_restful import Api, Resource
from http import HTTPStatus
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv('C:/Users/Jasmine/Desktop/learningScripts/laoshi-coach/laoshi/.env')

class MongoConnection():
    # Define class variables
    connection_str = os.getenv("MONGODB_CONNECTION_STRING")
    database = None
    
    @staticmethod
    def connect(database_name: str):
        try:
            client = MongoClient(MongoConnection.connection_str, server_api=ServerApi('1'))
            client.admin.command('ping')
            MongoConnection.database = client[database_name]
            print("Mongodb connected to database successfully")

        except Exception as e:
            print(f"Mongodb connection failed with: {e}")
            raise

    @staticmethod
    def list_all(collection_name: str) -> list[dict]:
        # this returns a list
        return list(MongoConnection.database[collection_name].find({}, {"_id":0}))
    
    @staticmethod
    def find_by_id(collection_name: str, id: int) -> dict:
        # this returns a dictionary
        return MongoConnection.database[collection_name].find_one({"id":id},{"_id":0})
    
    @staticmethod
    def count_all(collection_name: str) -> int:
        return int(MongoConnection.database[collection_name].count_documents({}))
    
    @staticmethod
    def insert(collection_name: str, data, isMultiple: bool) -> None:
        # data should contain isMultiple parameter and data parameter. Mongodb requires data to be in JSON format
        if isMultiple:
            num_items = len(data)
            MongoConnection.database[collection_name].insert_many(data)
            print(f"Successfully added {num_items} items into {collection_name}.")
        else:
            MongoConnection.database[collection_name].insert_one(data)
            print(f"Successfully added 1 item into {collection_name}.")

    @staticmethod
    def delete_by_id(collection_name: str, id: int) -> None:
        MongoConnection.database[collection_name].delete_one({"id":id})
        print(f"Successfully deleted 1 item from {collection_name}")

    @staticmethod
    def delete_all(collection_name: str) -> None:
        MongoConnection.database[collection_name].drop()
        MongoConnection.database.create_collection(collection_name)
        print(f"Successfully deleted {collection_name}")

    @staticmethod
    def update_by_id(collection_name: str, id: int, data) -> dict:
        word_to_update = MongoConnection.find_by_id(collection_name, id)

        # check for field mismatch before updating in MongoDB
        if not data.keys() <= word_to_update.keys():
            return {"error": "Missing required fields or fields do not match"}, 400
        
        MongoConnection.database[collection_name].update_one({"id": id}, {"$set": data})
        print(f"Successfully updated item with id {id} in {collection_name}")

        #re-query word with the updated fields and return it
        return MongoConnection.find_by_id(collection_name, id)


    @staticmethod
    def get_next_id(collection_name:str) -> int:
        last_document = MongoConnection.database[collection_name].find_one({},{"id": 1, "_id": 0},sort=[("id", -1)])
        if last_document:
            return int(last_document["id"]) + 1
        else:
            return 0


# Connect to database and set up app
MongoConnection.connect("test")
app = Flask(__name__)
api = Api(app)

class word():
    def __init__(self, word: str, pinyin: str, meaning: str, id=None):
        # id is assigned later during insertion
        self.id = id
        self.word = word
        self.pinyin = pinyin
        self.meaning = meaning
        self.confidence_score = 0.5
        self.status = 'Learning'

    def format_data(self):
        return {
            'id': self.id,
            'word': self.word,
            'pinyin': self.pinyin,
            'meaning': self.meaning,
            'confidence_score': self.confidence_score,
            'status': self.status
        }
    
    

class wordListResource(Resource):
    def get(self):
        try:
            words_list = MongoConnection.list_all("words")
        except Exception as e:
            return {"error": str(e)}, 500
        if words_list:
            return words_list, 200
        return {'message':'no words found'}, HTTPStatus.NOT_FOUND

    def post(self):
        try:
            data = request.get_json()
            word_to_add = None
            word_data = data["data"]
            rolling_id = MongoConnection.get_next_id("words")
            
            if data["isMultiple"] == True:
                list_of_word_data = []
                
                for item in word_data:
                    word_to_add = word(item["word"], item["pinyin"], item["meaning"], id=rolling_id)
                    list_of_word_data.append(word_to_add.format_data())
                    rolling_id += 1

                # MongoDB edits the list in place to add _id!
                MongoConnection.insert("words", list_of_word_data, isMultiple=True)
                return {'message':'Import successful.'}, HTTPStatus.CREATED
            else:
                word_to_add = word(word_data["word"], word_data["pinyin"], word_data["meaning"], id=rolling_id)
                MongoConnection.insert("words", word_to_add.format_data(), isMultiple=False)
                return {'message':'Import successful.'}, HTTPStatus.CREATED
            
        except Exception as e:
            return {"error": str(e)}, 500

            
    def delete(self):
        try:
            word_count = MongoConnection.count_all("words")
            MongoConnection.delete_all("words")
            success_message = f"{word_count} words successfully deleted."
            return {'message': success_message}, 204
        except Exception as e:
            return {"error": str(e)}, 500
        

class wordResource(Resource):
    def get(self, id:int):
        try:
            word = MongoConnection.find_by_id("words", id)
        except Exception as e:
            return {"error": str(e)}, 500
        if word:
            return word, 200
        return {'message':'word not found'}, HTTPStatus.NOT_FOUND
    
    def put(self, id:int):
        try:
            data = request.get_json()
            word = MongoConnection.find_by_id("words", id)
            if word:
                updated_word = MongoConnection.update_by_id("words", id, data)
                return updated_word, HTTPStatus.OK
            return {'message':'word not found'}, HTTPStatus.NOT_FOUND
            
        except Exception as e:
            return {"error": str(e)}, 500
        
    def delete(self, id:int):
        try:
            word = MongoConnection.find_by_id("words", id)
            if word:
                MongoConnection.delete_by_id("words", id)
                success_message = f"word {word["word"]} successfully deleted"
                return {'message': success_message}, HTTPStatus.OK
            return {'message':'word not found'}, HTTPStatus.NOT_FOUND
        
        except Exception as e:
            return {"error": str(e)}, 500
        
    #TODO: if delete by ID, there will be a hole in the running sequence!


class homeResource(Resource):
    def get(self):
        return "You have successfully called this API. Congrats!"
    
    def delete(self):
        return "This is a meaningless action, but have fun anyways."
        

api.add_resource(wordListResource, '/words')
api.add_resource(wordResource, '/words/<int:id>')
api.add_resource(homeResource, '/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

# class wordResource(Resource):
#     def get(self, word_id):
        
