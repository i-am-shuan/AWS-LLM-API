import asyncio
import websockets
import json

async def connect():
    # WebSocket API의 URL
    websocket_url = 'wss://l776hl36a4.execute-api.us-east-1.amazonaws.com/dev'

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
                'prompt': '다이어트에 도움이 되는 음식을 추천해줘.',
                'connectionId': connection_id
            })
        }
        await websocket.send(json.dumps(message))

        combined_response = ""  # 전체 응답 메시지를 저장할 변수

        try:
            async for message in websocket:
                print(f"Raw message received: {message}")
                
                # 수신된 메시지가 JSON 형식인지 확인
                try:
                    data = json.loads(message)
                    print('Received message:', data)

                    # 서버로부터 메시지를 수신했을 때 처리
                    if 'message' in data:
                        combined_response += data['message']
                        print('Response:', data['message'])
                    if data.get('type') == 'done':
                        print('Received done signal, closing connection.')
                        break

                except json.JSONDecodeError:
                    combined_response += message
                    print(f"Non-JSON message added: {message}")

        except websockets.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"Error: {e}")


        # 최종 합친 응답 메시지 출력
        print("###Response:", combined_response)

        # disconnect 메시지 전송
        disconnect_message = {
            'action': 'disconnect',
            'connectionId': connection_id
        }
        await websocket.send(json.dumps(disconnect_message))
        print("Sent disconnect message")

# WebSocket 연결 시작
asyncio.get_event_loop().run_until_complete(connect())
