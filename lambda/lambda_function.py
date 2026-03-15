import json, os, base64, hashlib, boto3
from datetime import datetime, timezone

s3_client = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
kms_client = boto3.client('kms')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE')
BUCKET_NAME = os.environ.get('S3_BUCKET')
KMS_KEY_ID = os.environ.get('KMS_KEY_ID')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        canonical_arn = body.get('canonical_arn')
        
        if not action or not canonical_arn:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing action or canonical_arn"})}

        # Fetch Diagram
        db_response = dynamodb.get_item(TableName=TABLE_NAME, Key={'CanonicalARN': {'S': canonical_arn}})
        if 'Item' not in db_response:
            return {"statusCode": 403, "body": json.dumps({"status": "DENIED", "reason": "No context diagram found."})}
        
        file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=db_response['Item']['DiagramS3Key']['S'])
        diagram_bytes = file_obj['Body'].read()

        # Nova Omni Call
        encoded_image = base64.b64encode(diagram_bytes).decode('utf-8')
        prompt = f"You are a Cloud Security Architect. An AI agent intends to execute '{action}' on resource '{canonical_arn}'. Step 1: Identify which element in this diagram corresponds to the ARN. Step 2: If deleted, does it sever a critical business path? Respond strictly in JSON: {{\"decision\": \"DENY\" or \"ALLOW\", \"reason\": \"evidence\"}}"
        
        payload = {"messages": [{"role": "user", "content": [{"image": {"format": "png", "source": {"bytes": encoded_image}}}, {"text": prompt}]}]}
        bedrock_response = bedrock.invoke_model(modelId="amazon.nova-pro-v1:0", body=json.dumps(payload), contentType="application/json", accept="application/json")
        nova_result = json.loads(json.loads(bedrock_response.get('body').read())['output']['message']['content'][0]['text'].replace('```json', '').replace('```', '').strip())
        
        if nova_result.get('decision') == 'DENY':
            return {"statusCode": 403, "body": json.dumps({"status": "DENIED BY NOVA OMNI", "reason": nova_result.get('reason')})}

        # KMS Attestation
        image_hash = hashlib.sha256(diagram_bytes).hexdigest()
        raw_string = f"{nova_result.get('reason')}|{image_hash}|{canonical_arn}|{datetime.now(timezone.utc).isoformat()}"
        sig_response = kms_client.sign(KeyId=KMS_KEY_ID, Message=raw_string.encode('utf-8'), MessageType='RAW', SigningAlgorithm='RSASSA_PKCS1_V1_5_SHA_256')
        
        return {"statusCode": 200, "body": json.dumps({
            "status": "APPROVED",
            "sts_session_policy": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": action, "Resource": canonical_arn}]},
            "session_tag": "sentinel:validated=true",
            "cryptographic_signature": base64.b64encode(sig_response['Signature']).decode('utf-8'),
            "diagram_hash": image_hash
        })}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
