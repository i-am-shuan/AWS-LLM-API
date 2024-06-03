import json
import boto3
import os
from botocore.exceptions import BotoCoreError, ClientError

def lambda_handler(event, context):
    print('@@@@@@@@@@@@@event: ', event)
    print('@@@@@@@@@@@@@context: ', context)

    try:
        body = json.loads(event['body'])
        prompt = body.get('prompt')
        connection_id = body.get('connectionId')

        if prompt:
            invoker = InvokeBedrock(connection_id)
            invoker.call_bedrock(prompt)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Request received'})
            }

        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid request'})
        }

    except KeyError as e:
        print(f"KeyError: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing key in event object'})
        }
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON'})
        }

class InvokeBedrock:
    def __init__(self, connection_id):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.conn = boto3.client('apigatewaymanagementapi', endpoint_url=os.environ['api_endpoint'], region_name=os.environ['region'])
        self.params = {
            "ConnectionId": connection_id,
            "Data": ""
        }

    def call_bedrock(self, request):
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        native_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 512,
            "temperature": 0.5,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": request}]
                }
            ]
        }

        request_payload = json.dumps(native_request)

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                body=request_payload
            )

            event_stream = response['body']
            for event in event_stream:
                print(f"Event received: {event}")

                if 'chunk' in event:
                    chunk_data = event['chunk']['bytes'].decode('utf-8')
                    chunk = json.loads(chunk_data)
                    print(chunk)
                    if chunk.get("type") == "content_block_delta":
                        message = chunk["delta"].get("text", "")
                        print(message, end="")
                        self.send_message_to_client(str(message))  # 문자열로 변환하여 전송
                    elif chunk.get("type") == "content_block_stop":
                        self.send_message_to_client(json.dumps({"type": "done"}))
                else:
                    print("No 'chunk' in event")

        except (BotoCoreError, ClientError) as error:
            print(error)
            self.params["Data"] = json.dumps({'error': str(error)})
            self.conn.post_to_connection(**self.params)

    def send_message_to_client(self, message):
        self.params["Data"] = json.dumps({"message": str(message)})  # 문자열로 변환하여 전송
        try:
            self.conn.post_to_connection(**self.params)
        except ClientError as e:
            print(f"Failed to send message to client: {e}")
