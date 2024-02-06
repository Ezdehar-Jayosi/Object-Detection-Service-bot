import telebot
from loguru import logger
import os
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import boto3
import json

class Bot:

    def __init__(self, token, telegram_chat_url):
        # create a new instance of the TeleBot class.
        # all communication with Telegram servers are done using self.telegram_bot_client
        self.telegram_bot_client = telebot.TeleBot(token)

        # remove any existing webhooks configured in Telegram servers
        self.telegram_bot_client.remove_webhook()
        time.sleep(0.5)

        # set the webhook URL
        self.telegram_bot_client.set_webhook(url=f'{telegram_chat_url}/{token}/',
                                             timeout=60,
                                             certificate=open("YOURPUBLIC.pem", 'r'))

        logger.info(f'Telegram Bot information\n\n{self.telegram_bot_client.get_me()}')

    def send_text(self, chat_id, text, reply_markup=None):
        self.telegram_bot_client.send_message(chat_id, text, reply_markup=reply_markup)
        logger.info(f'Sent text message to chat_id {chat_id}: {text}')

    def send_text_with_quote(self, chat_id, text, quoted_msg_id):
        self.telegram_bot_client.send_message(chat_id, text, reply_to_message_id=quoted_msg_id)
        logger.info(f'Sent text message to chat_id {chat_id} with quote: {text}')

    def is_current_msg_photo(self, msg):
        return 'photo' in msg

    def download_user_photo(self, msg):
        """
        Downloads the photos that sent to the Bot to `photos` directory (should be existed)
        :return:
        """
        if not self.is_current_msg_photo(msg):
            raise RuntimeError(f'Message content of type \'photo\' expected')

        file_info = self.telegram_bot_client.get_file(msg['photo'][-1]['file_id'])
        data = self.telegram_bot_client.download_file(file_info.file_path)
        folder_name = file_info.file_path.split('/')[0]

        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

        with open(file_info.file_path, 'wb') as photo:
            photo.write(data)
        logger.info(f'Downloaded photo from user with chat_id')
        return file_info.file_path

    def send_photo(self, chat_id, img_path):
        if not os.path.exists(img_path):
            raise RuntimeError("Image path doesn't exist")

        self.telegram_bot_client.send_photo(
            chat_id,
            InputFile(img_path)
        )
        logger.info(f'Sent photo to chat_id {chat_id}')

    def handle_message(self, msg):
        """Bot Main message handler"""
        logger.info(f'Incoming message: {msg}')
        self.send_text(msg['chat']['id'], f'Your original message: {msg["text"]}')


class ObjectDetectionBot(Bot):
    def __init__(self, telegram_chat_url):
        # Retrieve sensitive information from AWS Secrets Manager
        secrets_manager = boto3.client('secretsmanager', region_name='eu-west-3')

        telegram_token = self.get_secret('TELEGRAM_TOKEN', secrets_manager)
        self.s3_bucket_name = self.get_secret('S3_BUCKET_URL', secrets_manager)
        self.sqs_queue_url = self.get_secret('SQS_QUEUE_NAME', secrets_manager)

        super().__init__(telegram_token, telegram_chat_url)  # Specify the region here
        self.s3 = boto3.client('s3', region_name='eu-west-3')  # Specify the region here
        self.sqs = boto3.client('sqs', region_name='eu-west-3')  # Specify the region here

    def handle_message(self, msg):
        try:
            logger.info(f'Incoming message: {msg}')
            chat_id = msg['chat']['id']
            if 'new_chat_member' in msg:
                new_member = msg['new_chat_member']
                self.send_text(msg['chat']['id'], f'Welcome 😊\n'
                                                  'I am here to help you with object detection in images. '
                                                  'Simply send an image, and I *the bot* will process it for you.')

            elif self.is_current_msg_photo(msg):
                self.send_text(chat_id, "👍 Great! I received a photo. Analyzing... 🔍")
                img_path = self.download_user_photo(msg)

                # Call YOLOv5 for prediction here
                predicted_objects = self.predict_objects(img_path)

                # Upload the photo to S3
                s3_key = f'photos/{os.path.basename(img_path)}'
                self.upload_to_s3(img_path, s3_key)

                # Send a job to the SQS queue
                job_message = {
                    'photo_key': img_path,
                    'chat_id': chat_id
                }
                self.send_to_sqs(json.dumps(job_message))

                # Send a message to the Telegram end-user
                self.send_text(chat_id, '🤖 Your image is being processed. Please wait... ⏳')

                # Ask for feedback after prediction
                self.ask_for_feedback(chat_id)

            else:
                self.send_text(chat_id, "🚫 I can only process photos. Please send me a photo. 📷")
        except Exception as e:
            # Log the exception
            logger.error(f'Error handling message: {e}')

            # Send an error message to the user
            self.send_text(msg['chat']['id'],
                           'An error occurred while processing your request. Please try again later.')
        finally:
            logger.info('Exiting handle_message.')

    def ask_for_feedback(self, chat_id):
        # Ask the user for feedback using clickable buttons
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("Yes ✅", callback_data="feedback_yes"),
            InlineKeyboardButton("No ❌", callback_data="feedback_no")
        )
        self.send_text(chat_id, "Was the prediction successful?", reply_markup=keyboard)

    def handle_feedback(self, chat_id, feedback):
        if feedback.lower() == 'no':
            # If the prediction was not successful, ask the user what was wrong
            self.ask_for_wrong_prediction(chat_id)
        else:
            # If the prediction was successful, respond with a confirmation message
            self.send_text(chat_id, "Great! I'm glad the prediction was successful.")

    def ask_for_wrong_prediction(self, chat_id):
        # Ask the user which object was predicted incorrectly
        self.send_text(chat_id, "Which object was predicted incorrectly?")

    def handle_wrong_prediction(self, chat_id, wrong_prediction):
        # Respond with the corrected prediction
        self.send_text(chat_id, f"On second thought, it still looks like a {wrong_prediction}.")

    def predict_objects(self, img_path):
        # Call YOLOv5 for prediction
        # Replace this with your YOLOv5 prediction code
        return ["object1", "object2"]  # Example list of predicted objects

    def upload_to_s3(self, img_path, s3_key):
        try:
            self.s3.upload_file(img_path, self.s
