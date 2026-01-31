from http import HTTPStatus
from typing import Any, Callable, TypeVar, cast

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types

from careervp.handlers.utils.observability import logger
from careervp.models.exceptions import DynamicConfigurationException, InternalServerException
from careervp.models.output import InternalServerErrorOutput

E = TypeVar('E', bound=Exception)
HandlerFn = Callable[[E], Response[Any]]

app = APIGatewayRestResolver(enable_validation=True)
app.enable_swagger(path='/swagger', title='CareerVP API')


def typed_exception_handler(exc_type: type[E]) -> Callable[[Callable[[E], Response[Any]]], Callable[[E], Response[Any]]]:
    """Typed wrapper around APIGatewayRestResolver.exception_handler to satisfy mypy."""

    def decorator(func: Callable[[E], Response[Any]]) -> Callable[[E], Response[Any]]:
        return cast(Callable[[E], Response[Any]], app.exception_handler(exc_type)(func))

    return decorator


@typed_exception_handler(DynamicConfigurationException)
def handle_dynamic_config_error(ex: DynamicConfigurationException) -> Response[Any]:
    logger.exception('failed to load dynamic configuration from AppConfig')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )


@typed_exception_handler(InternalServerException)
def handle_internal_server_error(ex: InternalServerException) -> Response[Any]:
    logger.exception('finished handling request with internal error')
    return Response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR, content_type=content_types.APPLICATION_JSON, body=InternalServerErrorOutput().model_dump()
    )
