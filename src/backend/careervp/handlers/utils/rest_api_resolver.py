from http import HTTPStatus
from typing import Any

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types

from careervp.handlers.utils.observability import logger
from careervp.models.exceptions import DynamicConfigurationException, InternalServerException
from careervp.models.output import InternalServerErrorOutput

app = APIGatewayRestResolver(enable_validation=True)
app.enable_swagger(path='/swagger', title='CareerVP API')


# Powertools decorators are untyped; silence mypy while keeping the functions typed.
@app.exception_handler(DynamicConfigurationException)  # type: ignore[untyped-decorator]
def handle_dynamic_config_error(ex: DynamicConfigurationException) -> Response[Any]:  # receives exception raised
    logger.exception('failed to load dynamic configuration from AppConfig')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )


@app.exception_handler(InternalServerException)  # type: ignore[untyped-decorator]
def handle_internal_server_error(ex: InternalServerException) -> Response[Any]:  # receives exception raised
    logger.exception('finished handling request with internal error')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )
