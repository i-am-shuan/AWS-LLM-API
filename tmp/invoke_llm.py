import json
import boto3
import logging
import os
import html
import urllib.parse
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError
from langchain.llms.bedrock import Bedrock
from langchain.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from langchain.prompts import PromptTemplate

################################################################################################
region = 'us-east-1'
bedrock_client = boto3.client('bedrock-runtime', region_name = region)
bedrock_config = Config(connect_timeout=120, read_timeout=120, retries={'max_attempts': 0})
bedrock_agent_client = boto3.client("bedrock-agent-runtime", config=bedrock_config, region_name = region)
################################################################################################


def lambda_handler(event, context):
    print('@@@@@@@@@@@@@event: ', event)
    print('@@@@@@@@@@@@@context: ', context)

    try:
        body = json.loads(event['body'])
        query = body.get('prompt')
        connection_id = body.get('connectionId')

        retrieval_results = retrieve_rag(query)
        # print("@@retrieval_results: ", retrieval_results)
        
        min_score = 0.5
        filtered_results = [result for result in retrieval_results if result['score'] >= min_score]
        print("@@filtered_results: ", filtered_results)
        
        
        # context = get_contexts(filtered_results)
        
        html_output = generate_accessible_s3_urls(filtered_results)
        

        PROMPT_TEMPLATE = """
        Human: You are a financial advisor AI system, and provides answers to questions by using fact based and statistical information.
        Use the following pieces of information to provide a concise answer to the question enclosed in <question> tags.
        If you don't know the answer, just say that you don't know, don't try to make up an answer. Answer in Korean.
        <context>
        {context}
        </context>

        <question>
        {question}
        </question>

        The response should be specific and use statistics or numbers when possible.

        Assistant:"""
        
        prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])
        prompt_str = prompt.format(context=context, question=query)

        invoker = InvokeBedrock(connection_id)
        invoker.call_bedrock(prompt_str, html_output)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Request received'})
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

def retrieve_rag(query):
    try:
        numberOfResults=5
        kbId = "WCQI6NWIU3"
        
        relevant_documents = bedrock_agent_client.retrieve(
            retrievalQuery= {
                'text': query
            },
            knowledgeBaseId=kbId,
            retrievalConfiguration= {
                'vectorSearchConfiguration': {
                    'numberOfResults': numberOfResults,
                    # 'overrideSearchType': "HYBRID", # optional
                }
            }
        )
        
        print('@@@@@@@@@@@@@@relevant_documents: ', relevant_documents)
        return relevant_documents['retrievalResults']
    except Exception as e:
        print(f"error: {e}")
        return {'error': '예기치 않은 오류가 발생했습니다.', 'details': str(e)}

def get_contexts(retrievalResults):
    contexts = []
    for retrievedResult in retrievalResults: 
        contexts.append(retrievedResult['content']['text'])
        
    return contexts
    
def extract_uris_and_text(retrieval_results):
    uris = []
    texts = []
    for result in retrieval_results:
        if 'location' in result and 's3Location' in result['location'] and 'uri' in result['location']['s3Location']:
            uri = result['location']['s3Location']['uri']
            uris.append(uri)
        if 'content' in result and 'text' in result['content']:
            text = result['content']['text']
            texts.append(text)
    return uris, texts
    
def generate_public_s3_url(source_location):
    try:
        # source_location에서 버킷 이름과 키(파일 경로) 추출
        bucket_name, key = source_location.replace('s3://', '').split('/', 1)

        # 키를 URL 인코딩
        encoded_key = urllib.parse.quote(key)

        # 퍼블릭 URL 생성
        url = f"https://{bucket_name}.s3.amazonaws.com/{encoded_key}"

        return url
    except Exception as e:
        logger.error(e)
        return None

        
def generate_s3_url(source_location):
    try:
        # S3 클라이언트 생성
        s3 = boto3.client('s3')

        # source_location에서 버킷 이름과 키(파일 경로) 추출
        bucket_name, key = source_location.replace('s3://', '').split('/', 1)

        # 임시 URL 생성
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': key
            },
            ExpiresIn=3600  # 유효 기간(초)
        )

        return url
    except ClientError as e:
        logger.error(e)
        return None
    
def generate_accessible_s3_urls(retrieval_results):
    uris, texts = extract_uris_and_text(retrieval_results)
    
    print("@@@uris: ", uris)
    print("@@@texts: ", texts)
    
    html_output = ""
    first_time = True 
    processed_files = set()
    

    for i, uri in enumerate(uris):
        url = generate_public_s3_url(uri)
        file_name = uri.split('/')[-1]
        print('@@@url: ', url)
        print('@@@file_name: ', file_name)
        

        # 이미 처리된 파일명 SKIP
        if file_name not in processed_files:
            processed_files.add(file_name)
            
            if first_time:
                html_output += "\n\n📚 출처\n"
                first_time = False  # 이후 실행에서는 이 부분이 실행되지 않도록 플래그 변경

            html_output += f'{file_name} ({url})'
            # html_output += f'{file_name}'
    
    return html_output
    
    
    
###############################################################################################

class InvokeBedrock:
    def __init__(self, connection_id):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.conn = boto3.client('apigatewaymanagementapi', endpoint_url=os.environ['api_endpoint'], region_name=os.environ['region'])
        self.params = {
            "ConnectionId": connection_id,
            "Data": ""
        }



    def call_bedrock(self, request, html_output):
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
        
        
        ################
        # texts, uris, scores = [], [], []
        
        # for result in filtered_results:
        #     texts.append(result['content']['text'])
        #     uris.append(result['location']['s3Location']['uri'])
        #     scores.append(result['score'])
            
            
        # for uri in uris:
        #     print('@@@@@@@@uri: ', uri)    
            
        # url_score_list = [f"✅ {uri} ({score})" for uri, score in zip(uris, scores)]
        ################

        try:
            response = self.client.invoke_model_with_response_stream(
                modelId=model_id,
                contentType="application/json",
                body=request_payload
            )

            event_stream = response['body']
            
            for event in event_stream:
                if 'chunk' in event:
                    chunk_data = event['chunk']['bytes']
                    chunk = json.loads(chunk_data)
                    if chunk.get("type") == "content_block_delta":
                        message = chunk["delta"].get("text", "")
                        print(message, end="")
                        self.send_message_to_client(str(message))
                    elif chunk.get("type") == "content_block_stop":
                        # for item in url_score_list:
                        #     self.send_message_to_client('\n' + item)
                        
                        # print("@@@html_output: ", html_output)
                        self.send_message_to_client(html_output)
                        self.send_message_to_client(json.dumps({"type": "done"}))
                else:
                    print("No 'chunk' in event")

        except (BotoCoreError, ClientError) as error:
            print(error)
            self.params["Data"] = json.dumps({'error': str(error)})
            self.conn.post_to_connection(**self.params)
            
    def send_message_to_client(self, message):
        self.params["Data"] = json.dumps({"message": str(message)})
        try:
            self.conn.post_to_connection(**self.params)
        except ClientError as e:
            print(f"Failed to send message to client: {e}")
