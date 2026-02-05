# Alternative backend built with mongodb. kept aside for now

from flask import jsonify, Flask, request
from http import HTTPStatus
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv('../.env')
mongo_cluster = os.getenv("MONGODB_CONNECTION_STRING")

# connect to mongodb instance first
try:
    client = MongoClient(mongo_cluster, server_api=ServerApi('1'))
    # client.connect()
    client.admin.command('ping')
    db = client['test']
    collection = db['words']
    print("Mongodb connected successfully")

except Exception as e:
    print(f"Mongodb connection failed with: {e}")
    raise

app = Flask(__name__)

@app.route("/")
def alive():
    return "Server is alive."

@app.route("/words", methods=["GET"])
def get_words_list():
    # #get search query if any
    # data = request.get_json()
    # search_query = data.get('query')

    #query mongodb
    try:
        words_list = list(collection.find({}, {"_id":0}))
        # for word in words_list:
        #     word['_id'] = str(word['_id'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if words_list:
        return jsonify(words_list), 200

    return jsonify({'message':'no words found'}), HTTPStatus.NOT_FOUND


@app.route("/words/<int:id>", methods=['GET'])
def get_word_by_id(id):
    try:
        word = collection.find_one({"id": id}, {"_id":0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if word:
        return jsonify(word), 200

    return jsonify({'message':'word not found'}), HTTPStatus.NOT_FOUND

@app.route("/words", methods=['POST'])
def create_word():
    #get greatest id value in collection first
    try:
        last_word = collection.find_one({},{"id": 1, "_id": 0},sort=[("id", -1)])
        last_word_id = last_word["id"]
        if last_word_id:
            new_word_id = int(last_word_id) + 1
        else:
            new_word_id = 0
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    data = request.get_json()
    word = data.get('word')
    pinyin = data.get('pinyin')
    meaning = data.get('meaning')
    print(pinyin)

    json_to_add = {
        "id": new_word_id,
        "word": word,
        "pinyin": pinyin,
        "meaning": meaning
    }

    try:
        collection.insert_one(json_to_add)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return f"Word {word} successfully added."

@app.route("/words/<int:id>", methods=['DELETE'])
def delete_word_by_id(id):
    try:
        word_obj = collection.find_one({"id": id}, {"_id":0})
        word = word_obj["word"]
        collection.delete_one({"id": id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return f"Word {word} successfully deleted."


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)