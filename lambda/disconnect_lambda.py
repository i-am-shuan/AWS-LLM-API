import json
import boto3
import os

def lambda_handler(event, context):
    connection_id = event['requestContext']['connectionId']
    client = boto3.client('apigatewaymanagementapi', endpoint_url=os.environ['api_endpoint'], region_name=os.environ['region'])

    try:
        # 연결 종료
        client.delete_connection(ConnectionId=connection_id)
        return {
            'statusCode': 200,
            'body': json.dumps('Disconnected successfully')
        }
    except client.exceptions.GoneException:
        return {
            'statusCode': 410,
            'body': json.dumps('Connection already closed')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Failed to disconnect: {str(e)}')
        }
