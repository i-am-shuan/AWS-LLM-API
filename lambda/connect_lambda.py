import json

def lambda_handler(event, context):
    # requestContext에서 connectionId 추출
    connection_id = event.get('requestContext', {}).get('connectionId')
    
    if connection_id:
        print(f'Connection ID: {connection_id}')
        print('Connected successfully')
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Connected successfully', 'connectionId': connection_id})
        }
    else:
        print('Connection ID not found in requestContext')
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Connection ID not found in requestContext'})
        }
