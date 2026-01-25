# Custom exceptions and error handlers
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PrometheusError(Exception):
    '''Base exception for PROMETHEUS-NOVEL errors.'''
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception
        if original_exception:
            logger.error(f"PrometheusError: {message} (Original: {type(original_exception).__name__}: {original_exception})", exc_info=True)
        else:
            logger.error(f"PrometheusError: {message}")

class BudgetExceededError(PrometheusError):
    '''Raised when the LLM budget is exceeded.'''
    def __init__(self, message: str = "LLM budget exceeded."):
        super().__init__(message)
        logger.critical(f"BudgetExceededError: {message}")

class LLMGenerationError(PrometheusError):
    '''Raised when an LLM generation fails after retries/fallbacks.'''
    def __init__(self, message: str = "LLM generation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"LLMGenerationError: {message}")

class ValidationError(PrometheusError):
    '''Raised when data validation fails (e.g., Pydantic errors).'''
    def __init__(self, message: str = "Data validation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"ValidationError: {message}")

class MemoryError(PrometheusError):
    '''Raised for issues with memory management (e.g., vector store).'''
    def __init__(self, message: str = "Memory operation failed.", original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception)
        logger.error(f"MemoryError: {message}")

# Centralized error handler (example for a web API or main loop)
def handle_exception(e: Exception):
    '''
    Centralized handler for uncaught exceptions.
    Logs the error and provides a human-readable message.
    '''
    if isinstance(e, PrometheusError):
        # Prometheus custom errors are already logged with context
        logger.error(f"Handled Prometheus Error: {e.args[0]}")
    else:
        logger.exception(f"An unhandled critical error occurred: {e}") # Log full traceback
        # Graceful degradation / notification
        # metrics.increment_error_counter("critical_unhandled_error") # Example metric
    print(f"
CRITICAL ERROR: {e.args[0] if isinstance(e, PrometheusError) else 'An unexpected error occurred.'}")
    # In a production system, you might send alerts, shut down gracefully, etc.

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        raise BudgetExceededError("You ran out of money!")
    except PrometheusError as e:
        print(f"Caught: {e}")

    try:
        import requests # Simulate an external library error
        requests.get("http://nonexistent-url-12345.com")
    except Exception as e:
        handle_exception(e)

    try:
        raise LLMGenerationError("AI went rogue.", original_exception=ValueError("Bad output"))
    except PrometheusError as e:
        print(f"Caught: {e}")
