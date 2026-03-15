import aws_cdk as core
import aws_cdk.assertions as assertions

from sentinel_live.sentinel_live_stack import SentinelLiveStack

# example tests. To run these tests, uncomment this file along with the example
# resource in sentinel_live/sentinel_live_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SentinelLiveStack(app, "sentinel-live")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
