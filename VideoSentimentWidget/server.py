from bson.json_util import dumps
from flask import Flask, request, render_template, Response, jsonify
import json
import OpenSSL
import os.path
from pymongo import MongoClient
import re
import requests

# Create new database for transcripts
client = MongoClient()
db = client.transcript_database
try:
    import config
    db.authenticate(config.user, config.pwd)
except ImportError:
    pass
collection = ''

# More info: http://flask.pocoo.org/docs/quickstart/
app = Flask(__name__)

# Get template on page load
@app.route('/')
def template():
    return render_template('video.html')

# Get phrase, calculate sentiment, and return score
@app.route('/sentiment/<phrase>')
def sentiment(phrase):
    # More info: https://github.com/gsi-upm/SEAS
    requestData = {
        'input': phrase.strip(),
        'informat': 'text',
        'intype': 'direct',
        'outformat': 'json-ld',
        'algo': request.args.get('name', type=str)
    }

    # Send to correct server address
    if request.args.get('restricted', type=str) == 'true':
        link = 'http://demos.gsi.dit.upm.es/tomcat/RestrictedToNIF/RestrictedService'
    else:
        link = 'http://demos.gsi.dit.upm.es/tomcat/SAGAtoNIF/Service'
    # Send request for sentiment analysis
    result = requests.post(link, requestData)
    # Decode as JSON and parse
    score = result.json()['entries'][0]['opinions'][0]['marl:polarityValue']
    print result.text
    return Response(str(score))

# Called for accessing a collection and obtaining a list of available
# collection names
@app.route('/retrieve/<collectionName>')
def retrieveCollection(collectionName):
    # If a collection name was provided, get documents in that collection
    # Note: collection name is the same as the video name originally provided
    if collectionName.strip():
        selectedCollection = db[collectionName]
        print("Accessing: '{}'".format(collectionName))
        # Make sure a new collection was not created, if so delete it and abort
        if not selectedCollection.count():
            selectedCollection.drop()
            print "Error: tried to access nonexistent or empty collection!"
            return jsonify({'status': 400})
        # Loop through the documents in the collection and return a json list
        # of the ones that are not empty. There shouldn't be any empty,
        # but in case there are this prevents an error on the receiving end
        return dumps([document for document
                      in selectedCollection.find()
                    ])
    # If no name was specified return a list of collection names
    # Note: regular expression is to prevent inclusion of the system database
    regex = re.compile('^system.')
    collections = [name for name
                   in db.collection_names()
                   if not re.match(regex, name)]
    print ';; '.join(collections)
    return Response(';; '.join(collections))

# Create development server with automatic SSL credentials
# NOTE: Without SSL, microphone permission is repeatedly requested
if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=8675, ssl_context='adhoc')
