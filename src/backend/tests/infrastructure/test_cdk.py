from aws_cdk import App, Environment
from aws_cdk.assertions import Template
from cdk.careervp.naming_utils import NamingUtils
from cdk.careervp.service_stack import ServiceStack


def test_synthesizes_properly():
    app = App()
    naming = NamingUtils(environment='dev', region='us-east-1', account_id='123456789012')

    service_stack = ServiceStack(
        app,
        'service-test',
        is_production_env=True,
        naming=naming,
        stack_feature='crud',
        env=Environment(account='123456789012', region='us-east-1'),
    )

    # Prepare the stack for assertions.
    template = Template.from_stack(service_stack)

    # verify that we have one API GW, that is it not deleted by mistake
    template.resource_count_is('AWS::ApiGateway::RestApi', 1)
    # main db, idempotency table, and vpr_jobs table for async processing
    template.resource_count_is('AWS::DynamoDB::GlobalTable', 3)
