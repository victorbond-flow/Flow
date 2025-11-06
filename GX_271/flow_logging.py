# flow_logging.py (placed in VictorFlow/Logs)
from loguru import logger
from pathlib import Path
import functools
import time

class FlowLogger:
    def __init__(self, log_dir=None):
        # Use provided log_dir or default to VictorFlow/Logs
        self.log_dir = Path(log_dir or Path().resolve() / "Logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Remove default loguru handler
        logger.remove()

        # Add file handlers
        logger.add(self.log_dir / "DEBUG.txt", level="DEBUG",
                   format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)
        logger.add(self.log_dir / "INFO.txt", level="INFO",
                   filter=lambda r: r["level"].name == "INFO",
                   format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)
        logger.add(self.log_dir / "ERROR.txt", level="ERROR",
                   filter=lambda r: r["level"].name == "ERROR",
                   format="[{time:DD/MM/YY HH:mm:ss}] | {level} | {message}", enqueue=True)

        self.logger = logger

    # Decorator to log function calls
    def log_call(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            arg_list = [repr(a) for a in args[1:]]  # skip self
            arg_list += [f"{k}={v!r}" for k, v in kwargs.items()]
            arg_str = ", ".join(arg_list)
            try:
                self.logger.debug(f"CALL {func.__name__}({arg_str})")
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                self.logger.debug(f"RETURN {func.__name__} -> {result!r} (Duration: {duration:.3f}s)")
                return result
            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(f"EXCEPTION in {func.__name__} after {duration:.3f}s: {e}")
                raise
        return wrapper

    # Simple log methods
    def info(self, msg): self.logger.info(msg)
    def debug(self, msg): self.logger.debug(msg)
    def error(self, msg): self.logger.error(msg)


