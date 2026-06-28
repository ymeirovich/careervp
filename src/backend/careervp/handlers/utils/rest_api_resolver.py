from collections.abc import Callable
from http import HTTPStatus
from typing import Any, TypeVar, cast

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types

from careervp.handlers.utils.observability import logger
from careervp.models.exceptions import DynamicConfigurationException, InternalServerException
from careervp.models.output import InternalServerErrorOutput

app = APIGatewayRestResolver(enable_validation=True)
app.enable_swagger(path='/swagger', title='CareerVP API')

ExceptionT = TypeVar('ExceptionT', bound=Exception)
ExceptionHandler = Callable[[ExceptionT], Response[Any]]
ExceptionHandlerDecorator = Callable[[ExceptionHandler[ExceptionT]], ExceptionHandler[ExceptionT]]


def typed_exception_handler(exception_type: type[ExceptionT]) -> ExceptionHandlerDecorator[ExceptionT]:
    return cast(ExceptionHandlerDecorator[ExceptionT], app.exception_handler(exception_type))


@typed_exception_handler(DynamicConfigurationException)
def handle_dynamic_config_error(ex: DynamicConfigurationException) -> Response[Any]:  # receives exception raised
    logger.exception('failed to load dynamic configuration from AppConfig')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )


@typed_exception_handler(InternalServerException)
def handle_internal_server_error(ex: InternalServerException) -> Response[Any]:  # receives exception raised
    logger.exception('finished handling request with internal error')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )
