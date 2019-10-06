from flask import Flask, request, jsonify
import requests
import json
import os


app = Flask(__name__)

CLIENT_ID = os.environ['SLACK_APP_PONG_CLIENT_ID']
CLIENT_SECRET = os.environ['SLACK_APP_PONG_CLIENT_SECRET']

@app.route("/")
def home():
    return "Hello, World!"

@app.route('/oauth', methods = ['GET'])
def oauth():
    code = request.args.get('code')
    if not code:
        return 'code missing', 500

    r = requests.get(url='https://slack.com/api/oauth.access', params={
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    })

    response = json.loads(r.text)
    return response  # TODO what to actually return here?


@app.route("/command", methods = ['POST'])
def command():
    return "Command!"

if __name__ == "__main__":
    app.run(debug=True)
