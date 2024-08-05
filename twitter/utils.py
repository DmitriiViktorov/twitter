import logging
import sys
from functools import wraps

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger_handler = logging.StreamHandler(stream=sys.stdout)
logger_handler.setFormatter(logging.Formatter(
    fmt='[%(asctime)s: %(levelname)s] %(message)s',
))
logger.addHandler(logger_handler)


def log_function_calls(logger):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            logger.info(f"Function {func.__name__} executed with args: {args}, kwargs: {kwargs}. Result: {result}")
            return result
        return wrapper
    return decorator
