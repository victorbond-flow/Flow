from loguru import logger
from datetime import datetime
from pathlib import Path
import time
import functools

# -------------------------------
# 1. CREATE LOG DIRECTORY
# -------------------------------
LOG_DIR = Path(r"C:\Users\40299205\Documents\VictorFlow\Logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)  # creates folder if not exists

# -------------------------------
# 2. REMOVE DEFAULT HANDLER
# -------------------------------
logger.remove()

# -------------------------------
# 3. ADD SEPARATE FILE HANDLERS
# -------------------------------
# DEBUG: everything
logger.add(LOG_DIR / "DEBUG.txt", level="DEBUG",
           format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)

# INFO: info only
logger.add(LOG_DIR / "INFO.txt", level="INFO",
           filter=lambda record: record["level"].name == "INFO",
           format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)

# ERROR: errors only
logger.add(LOG_DIR / "ERROR.txt", level="ERROR",
           filter=lambda record: record["level"].name == "ERROR",
           format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)

# -------------------------------
# 4. DECORATOR TO AUTO-LOG FUNCTION CALLS
# -------------------------------
def log_call(func):
    """
    Logs function call, arguments, execution duration, and any errors.
    Usage:
        @log_call
        def foo(x, y): ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        # Build argument string
        arg_list = []
        if args:
            arg_list += [repr(a) for a in args[1:]]  # skip self
        if kwargs:
            arg_list += [f"{k}={v!r}" for k, v in kwargs.items()]
        arg_str = ", ".join(arg_list)

        try:
            logger.debug(f"CALL {func.__name__}({arg_str})")
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"RETURN {func.__name__} -> {result!r} (Duration: {duration:.3f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"EXCEPTION in {func.__name__} after {duration:.3f}s: {e}")
            raise

    return wrapper

# -------------------------------
# 5. SIMPLE LOGGING FUNCTIONS
# -------------------------------
def log_info(msg: str):
    logger.info(msg)

def log_debug(msg: str):
    logger.debug(msg)

def log_error(msg: str):
    logger.error(msg)
