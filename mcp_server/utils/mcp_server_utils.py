import inspect
import logging
import time
import traceback
from functools import wraps


def tool_wrapper(func):
    """Decorator để tự động log thời gian chạy, kết quả chạy của tool.
    Có thể chạy được với cả hàm sync và async."""

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                end = time.perf_counter()
                logging.info(
                    f"✅ Tool {func.__name__} executed in {end - start:.4f}s. "
                    f"Args={args}, Kwargs={kwargs}, Result={result}"
                )
                return result
            except Exception:
                end = time.perf_counter()
                logging.error(
                    f"❌ Error in tool {func.__name__} after {end - start:.4f}s "
                    f"with args={args}, kwargs={kwargs}\n{traceback.format_exc()}"
                )
                return "Tool call failed. Something went wrong."

        return async_wrapper
    else:

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                end = time.perf_counter()
                logging.info(
                    f"✅ Tool {func.__name__} executed in {end - start:.4f}s. "
                    f"Args={args}, Kwargs={kwargs}, Result={result}"
                )
                return result
            except Exception:
                end = time.perf_counter()
                logging.error(
                    f"❌ Error in tool {func.__name__} after {end - start:.4f}s "
                    f"with args={args}, kwargs={kwargs}\n{traceback.format_exc()}"
                )
                return "Tool call failed. Something went wrong."

        return sync_wrapper
