import time
from pathlib import Path
from detect import run
import yaml
from loguru import logger
import os
import boto3
import requests
import json
from decimal import Decimal

# Retrieve sensitive information from AWS Secrets Manager
secrets_manager = boto3.client('secretsmanager', region_name='eu-west-3')

def get_secret(secret_name):
    try:
        secret_response = secrets_manager.get_secret_value(SecretId=secret_name)
        return json.loads(secret_response['SecretString'])
    except Exception as e:
        logger.error(f"Error retrieving secret '{secret_name}': {e}")
        raise

secrets = get_secret('ezdehar-secret')

images_bucket = secrets['BUCKET_NAME']
queue_name = secrets['SQS_QUEUE_NAME']
polybot_url = 'https://ezdehar-alb-57890755.eu-west-3.elb.amazonaws.com/results/'  # Replace with the actual ALB URL of Polybot

sqs_client = boto3.client('sqs', region_name='eu-west-3')

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']



def consume():
    while True:
        response = sqs_client.receive_message(QueueUrl=queue_name, MaxNumberOfMessages=1, WaitTimeSeconds=5)

        if 'Messages' in response:
            message = response['Messages'][0]['Body']
            receipt_handle = response['Messages'][0]['ReceiptHandle']

            # Use the ReceiptHandle as a prediction UUID
            prediction_id = response['Messages'][0]['MessageId']

            logger.info(f'prediction: {prediction_id}. start processing')

            # Receives parameters from the message
            message_body = json.loads(message)
            img_name = message_body.get('photo_key')
            chat_id = message_body.get('chat_id')
           # original_img_path = f'{img_name}'
            logger.info(f'S3 Bucket: {images_bucket}, Image Name: {img_name}')

            original_img_path = download_from_s3(img_name, prediction_id)

            logger.info(f'prediction: {prediction_id}/{original_img_path}. Download img completed')

            # Predicts the objects in the image
            run(
                weights='yolov5s.pt',
                data='data/coco128.yaml',
                source=original_img_path,
                project='static/data',
                name=prediction_id,
                save_txt=True
            )

            logger.info(f'prediction: {prediction_id}/{original_img_path}. done')

            # This is the path for the predicted image with labels
            predicted_img_path = Path(f'static/data/{prediction_id}/{original_img_path}')

            # Upload the predicted image to S3 (do not override the original image)
            # Debug prints
            print(f"Before upload_to_s3: Local file exists: {os.path.exists(predicted_img_path)}")
            print(f"Local directory exists: {os.path.exists(predicted_img_path.parent)}")

            upload_to_s3(predicted_img_path, f'predicted_images/{prediction_id}/{original_img_path}')

            # Debug prints
            print(f"After upload_to_s3: Local file exists: {os.path.exists(predicted_img_path)}")

            # Parse prediction labels and create a summary
            pred_summary_path = Path(f'static/data/{prediction_id}/labels/{original_img_path.name.split(".")[0]}.txt')


            if pred_summary_path.exists():
                labels = parse_labels(pred_summary_path)
                logger.info(f'prediction: {prediction_id}/{original_img_path}. prediction summary:\n\n{labels}')

                prediction_summary = {
                    'prediction_id': prediction_id,
                    'chat_id': chat_id,
                    'original_img_path': str(original_img_path),
                    'predicted_img_path': str(predicted_img_path),
                    'labels': labels,
                    'time': time.time()
                }

                # Store the prediction_summary in a DynamoDB table
                store_in_dynamodb(prediction_summary)

                # Perform a GET request to Polybot's /results endpoint
                send_results_to_polybot(prediction_summary)

            # Delete the message from the queue as the job is considered as DONE
            sqs_client.delete_message(QueueUrl=queue_name, ReceiptHandle=receipt_handle)


def download_from_s3(img_name, prediction_id):
    # Remove 'photos/' prefix if it exists in img_name
    img_name_without_prefix = img_name[len('photos/'):] if img_name.startswith('photos/') else img_name
    local_directory = Path("photos")
    local_directory.mkdir(parents=True, exist_ok=True)
    local_file_path = local_directory / f'{prediction_id}.jpg'

    try:
        boto3.client('s3').download_file(images_bucket, img_name_without_prefix, str(local_file_path))
    except Exception as e:
        logger.error(f'Error downloading image from S3: {e}')
        raise

    return local_file_path

def upload_to_s3(local_path, s3_key):
    try:
        local_file_path = Path(local_path)
        local_directory = local_file_path.parent

        # Debug prints
        print(f"Before upload_to_s3: Local file exists: {local_file_path.exists()}")
        print(f"Local directory exists: {local_directory.exists()}")

        # Check if the local file exists before attempting the upload
        if not local_file_path.exists():
            print(f"Local file does not exist: {local_file_path}")
            return

        # Upload the file to S3
        boto3.client('s3').upload_file(str(local_file_path), images_bucket, s3_key)

        # Debug print
        print(f"After upload_to_s3: Local file exists: {local_file_path.exists()}")
    except Exception as e:
        logger.error(f'Error uploading to S3: {e}')
        raise


def parse_labels(pred_summary_path):
    with open(pred_summary_path) as f:
        labels = f.read().splitlines()
        labels = [line.split(' ') for line in labels]
        labels = [{
            'class': names[int(l[0])],
            'cx': float(l[1]),
            'cy': float(l[2]),
            'width': float(l[3]),
            'height': float(l[4]),
        } for l in labels]

    return labels


def convert_floats_to_decimal(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(element) for element in obj]
    return obj


def store_in_dynamodb(prediction_summary):
    try:
        prediction_summary = convert_floats_to_decimal(prediction_summary)
        boto3.resource('dynamodb', region_name='eu-west-3').Table('ezdehar-table').put_item(Item=prediction_summary)

    except Exception as e:
        logger.error(f'Error storing in DynamoDB: {e}')
        raise


def send_results_to_polybot(prediction_summary):
    try:
        headers = {'Content-Type': 'application/json'}  # Add any other headers as needed
        print("Request Headers:", headers)  # Add this line to print headers
        pb_url = polybot_url + '/results/'
        response = requests.get(polybot_url, params={'predictionId': prediction_summary['prediction_id']},
                                headers=headers, verify=False)
        response.raise_for_status()
        print(f"Response content: {response.content}")
        # response.raise_for_status()
        if response.status_code == 200:
            logger.info("GET request to bot was successful.")
            # logger.info("Response:", get_response.json())
        else:
            logger.info("GET request to bot failed.")
            # logger.info("Status Code:", get_response.status_code)

    except requests.exceptions.RequestException as e:
        logger.error(f'Error sending results to Polybot: {e}')
        raise


if __name__ == "__main__":
    consume()
