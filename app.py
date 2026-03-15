import aws_cdk as cdk
from aws_cdk import (
    Stack, aws_s3 as s3, aws_dynamodb as dynamodb, aws_kms as kms, 
    aws_lambda as _lambda, aws_apigateway as apigw, aws_iam as iam, RemovalPolicy, CfnOutput
)
from constructs import Construct

class SentinelStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vault_bucket = s3.Bucket(self, "DiagramVault", removal_policy=RemovalPolicy.DESTROY, auto_delete_objects=True)
        resource_index = dynamodb.Table(self, "ResourceIndex", partition_key=dynamodb.Attribute(name="CanonicalARN", type=dynamodb.AttributeType.STRING), removal_policy=RemovalPolicy.DESTROY)
        sentinel_key = kms.Key(self, "SentinelKmsKey", key_spec=kms.KeySpec.RSA_2048, key_usage=kms.KeyUsage.SIGN_VERIFY, removal_policy=RemovalPolicy.DESTROY)
        
        sentinel_lambda = _lambda.Function(self, "SentinelLogic", 
            runtime=_lambda.Runtime.PYTHON_3_12, handler="lambda_function.lambda_handler", 
            code=_lambda.Code.from_asset("lambda"), 
            environment={"S3_BUCKET": vault_bucket.bucket_name, "DYNAMODB_TABLE": resource_index.table_name, "KMS_KEY_ID": sentinel_key.key_id}
        )
        
        vault_bucket.grant_read(sentinel_lambda)
        resource_index.grant_read_data(sentinel_lambda)
        sentinel_key.grant(sentinel_lambda, "kms:Sign")
        sentinel_lambda.add_to_role_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"]))
        
        api = apigw.LambdaRestApi(self, "SentinelApi", handler=sentinel_lambda)
        
        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "BucketName", value=vault_bucket.bucket_name)
        CfnOutput(self, "TableName", value=resource_index.table_name)

app = cdk.App()
SentinelStack(app, "SentinelStack")
app.synth()
