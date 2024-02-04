import flask
from flask import request
import os
from bot import ObjectDetectionBot
import boto3
import json
from botocore.exceptions import ClientError
from flask import abort
from loguru import logger

app = flask.Flask(__name__)


def format_prediction_results(prediction_result):
    # Extract relevant information from the prediction result
    prediction_id = prediction_result["prediction_id"]
    labels = prediction_result["labels"]

    # Create a dictionary to store the count of each detected object
    object_counts = {}

    # Iterate over each label in the prediction result
    for label in labels:
        class_name = label["class"]
        object_counts[class_name] = object_counts.get(class_name, 0) + 1

    # Convert the object counts dictionary to a formatted string
    formatted_results = ", ".join(f"{obj}: {count}" for obj, count in object_counts.items())

    return f"Detected objects: {formatted_results}"
def setup_routes():
    @app.route('/', methods=['GET'])
    def index():
        logger.info('Received a GET request on /')
        return 'Ok'

    @app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
    def webhook():
        req = request.get_json()
        logger.info(f"Received a POST request on /{TELEGRAM_TOKEN}/: {req}")
        bot.handle_message(req['message'])
        return 'Ok'

    @app.route(f'/results/', methods=['GET'])
    def results():
        try:
            prediction_id = request.args.get('predictionId')
            logger.info(f"Received a GET request on /results/ with predictionId={prediction_id}")
            # Check if prediction_id is provided
            if not prediction_id:
                return 'Prediction ID not provided', 400

            # Retrieve results from DynamoDB
            response = dynamodb_table.get_item(Key={'prediction_id': prediction_id})
            result_item = response.get('Item', {})

            # Check if the result_item is empty
            if not result_item:
                # Return a 404 Not Found response if no data is found for the given prediction_id
                return 'No data found for the given Prediction ID', 404

            # Extract chat_id and text_results from the DynamoDB result_item
            chat_id = result_item.get('chat_id')
            text_results = format_prediction_results(result_item)

            bot.send_text(chat_id, text_results)
            return 'Results sent successfully'

        except ClientError as dynamodb_error:
            # Log the DynamoDB error for debugging purposes
            logger.error(f"DynamoDB Error: {dynamodb_error}")

            # Return a 500 Internal Server Error response with a specific error message
            return 'Error retrieving data from DynamoDB', 500
        except Exception as e:
            # Log the general exception for debugging purposes
            logger.error(f"Error processing results: {e}")

            # Return a 500 Internal Server Error response with a generic error message
            return 'Internal Server Error', 500

    @app.route(f'/loadTest/', methods=['POST'])
    def load_test():
        req = request.get_json()
        logger.info(f"Received a POST request on /loadTest/: {req}")
        bot.handle_message(req['message'])
        return 'Ok'


if __name__ == "__main__":
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name='eu-west-3'
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId='ezdehar-secret'
        )
    except ClientError as error:
        raise error

    secrets = json.loads(get_secret_value_response['SecretString'])
    TELEGRAM_TOKEN = secrets['TELEGRAM_TOKEN']
    TELEGRAM_APP_URL = 'https://ezdeharbot.atech-bot.click/'
    #TELEGRAM_APP_URL = 'aa7efeb52e00748a897a58c171caab79-2082a31a9ce5a082.elb.us-east-1.amazonaws.com'
    DYNAMODB_REGION = 'eu-west-3'
    DYNAMODB_TABLE_NAME = 'ezdehar-table'
    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    dynamodb_table = dynamodb.Table(DYNAMODB_TABLE_NAME)

    # Create an instance of ObjectDetectionBot
    bot = ObjectDetectionBot(TELEGRAM_APP_URL)

    # Call setup_routes to define routes
    setup_routes()

    # Run the app
    app.run(host='0.0.0.0', port=8443)