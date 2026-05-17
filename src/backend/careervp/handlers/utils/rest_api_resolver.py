import os
from http import HTTPStatus
from typing import Any, Callable

from aws_lambda_powertools.event_handler import APIGatewayRestResolver, Response, content_types

from careervp.handlers.utils.observability import logger
from careervp.models.exceptions import DynamicConfigurationException, InternalServerException
from careervp.models.output import InternalServerErrorOutput

_ALLOWED_ORIGINS: set[str] = {o.strip() for o in os.getenv('ALLOWED_ORIGINS', '').split(',') if o.strip()}


def _cors_middleware(app: APIGatewayRestResolver, next_middleware: Callable[..., Any]) -> Response[Any]:
    response: Response[Any] = next_middleware(app)
    raw_headers: dict[str, str] = app.current_event.headers or {}
    origin = raw_headers.get('origin') or raw_headers.get('Origin')
    if origin and origin in _ALLOWED_ORIGINS:
        if response.headers is None:
            response.headers = {}
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response


app = APIGatewayRestResolver(enable_validation=True)
app.enable_swagger(path='/swagger', title='CareerVP API')
app.use(middlewares=[_cors_middleware])


# Powertools' exception handler decorator is currently untyped in our stubs.
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
