class PortalAutomationError(Exception):
    def __init__(self, *, portal: str, operation: str, reason: str) -> None:
        self.portal = portal
        self.operation = operation
        self.reason = reason
        super().__init__(f"{portal}:{operation} failed: {reason}")


class TransientPortalError(PortalAutomationError):
    pass


class ValidationFailedError(PortalAutomationError):
    pass


class ConfigurationError(Exception):
    pass
