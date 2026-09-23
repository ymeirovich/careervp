import functools
from collections.abc import Callable
from typing import Any, cast

from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.metrics import Metrics
from aws_lambda_powertools.tracing import Tracer

METRICS_NAMESPACE = 'careervp_kpi'

# JSON output format, service name can be set by environment variable "POWERTOOLS_SERVICE_NAME"
logger: Logger = Logger()

# service name can be set by environment variable "POWERTOOLS_SERVICE_NAME". Disabled by setting POWERTOOLS_TRACE_DISABLED to "True"
tracer: Tracer = Tracer()

# namespace and service name can be set by environment variable "POWERTOOLS_METRICS_NAMESPACE" and "POWERTOOLS_SERVICE_NAME" accordingly
metrics = Metrics(namespace=METRICS_NAMESPACE)


def log_response_status[HandlerT: Callable[..., Any]](handler: HandlerT) -> HandlerT:
    """Emit the outgoing HTTP status code on the handler's structured log line.

    The API Gateway access log records what the *gateway* returned; this
    records what the *handler* decided, keyed so it can be filtered. Without
    it a 401 and a 409 are indistinguishable in CloudWatch Logs — which is
    exactly where the 2026-08-04 audit stalled when it tried to split security
    4xx from contract 4xx.

    Applied closest to the function so it runs inside
    ``logger.inject_lambda_context`` and inherits the correlation id. Every
    return path is covered, including early returns; a raised exception is
    re-raised unchanged after being logged as an unhandled failure.
    """

    @functools.wraps(handler)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            response = handler(*args, **kwargs)
        except Exception:
            logger.append_keys(status_code=500)
            logger.exception('request failed with an unhandled exception', status_code=500)
            raise

        status_code = response.get('statusCode') if isinstance(response, dict) else None
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            # Worker/queue handlers return no statusCode. Powertools keys persist
            # across invocations in a warm container, so drop the key rather than
            # leaving the previous request's status attached to this one.
            logger.remove_keys(['status_code'])
            return response

        logger.append_keys(status_code=status_code)
        logger.info('request completed', status_code=status_code)
        return response

    return cast(HandlerT, wrapper)
