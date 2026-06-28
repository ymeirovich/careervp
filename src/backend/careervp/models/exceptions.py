class InternalServerException(Exception):
    pass


class DynamicConfigurationException(Exception):
    pass


class InvalidVersionError(Exception):
    pass


class InvalidStateTransitionError(ValueError):
    """Raised when an application state transition is not permitted.

    Subclasses ValueError for backward compatibility with callers/tests that
    catch the broader type.
    """

    pass
