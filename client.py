import asyncio
import websockets
import json

async def connect():
    # WebSocket API의 URL
    websocket_url = 'wss://l776hl36a4.execute-api.us-east-1.amazonaws.com/prod'

    async with websockets.connect(websocket_url) as websocket:
        print("WebSocket connection opened")

        # 연결 후 connectionID를 서버로부터 받기 위해 초기 메시지를 전송
        connect_message = {
            'action': '$connect'
        }
        await websocket.send(json.dumps(connect_message))
        
        # 서버로부터 connectionID 수신
        connection_response = await websocket.recv()
        print(f"Connection response: {connection_response}")
        connection_data = json.loads(connection_response)
        connection_id = connection_data.get('connectionId')
        print(f"Connection ID: {connection_id}")

        # 실제 메시지 전송
        message = {
            'action': 'sendMessage',
            'body': json.dumps({
                'prompt': 'Hello, Bedrock!',
                'connectionId': connection_id
            })
        }
        await websocket.send(json.dumps(message))

        buffer = ""  # 메시지를 저장할 버퍼

        try:
            async for message in websocket:
                print(f"Raw message received: {message}")
                
                # 수신된 메시지가 JSON 형식인지 확인
                try:
                    data = json.loads(message)
                    print('Received message:', data)

                    # 서버로부터 메시지를 수신했을 때 처리
                    if data.get('type') == 'response':
                        print('Response:', data.get('message'))
                    elif data.get('type') == 'done':
                        print('Received done signal, closing connection.')
                        break

                except json.JSONDecodeError:
                    # JSON 디코드 오류가 발생하면 텍스트 메시지로 간주하고 처리
                    print(f"Non-JSON message received: {message}")
                    continue

        except websockets.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"Error: {e}")

        # disconnect 메시지 전송
        disconnect_message = {
            'action': 'disconnect',
            'connectionId': connection_id
        }
        await websocket.send(json.dumps(disconnect_message))
        print("Sent disconnect message")

# WebSocket 연결 시작
asyncio.get_event_loop().run_until_complete(connect())
