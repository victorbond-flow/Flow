# flow_logging.py (placed in VictorFlow/Logs)
from loguru import logger
from pathlib import Path
import functools
import time


class FlowLogger:
    def __init__(self, log_dir=None):
        """
        Initialise the FlowLogger and set up all log files.

        Creates a logging directory (default: ./Logs/) and configures Loguru
        to write three separate log files:

            DEBUG.txt  – everything (full detail of program execution)
            INFO.txt   – only important workflow-level messages
            ERROR.txt  – only errors and exceptions

        Any existing Loguru handlers are removed so only these files are used.
        """

        self.log_dir = Path(log_dir or Path().resolve() / "Logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Track which experiment the logs belong to
        self.current_experiment = None

        # Remove default loguru handler
        logger.remove()

        # ---- Shared log format (adds EXP:{experiment}) ----
        # Using {extra[experiment]} allows dynamic updating through bind()
        log_format = (
            "[{time:DD/MM/YY HH:mm:ss}] | {level} | EXP:{extra[experiment]} | {message}"
        )

        # Add file handlers, each with experiment tagging support
        logger.add(
            self.log_dir / "DEBUG.txt", level="DEBUG", format=log_format, enqueue=True
        )

        logger.add(
            self.log_dir / "INFO.txt",
            level="INFO",
            filter=lambda r: r["level"].name == "INFO",
            format=log_format,
            enqueue=True,
        )

        logger.add(
            self.log_dir / "ERROR.txt",
            level="ERROR",
            filter=lambda r: r["level"].name == "ERROR",
            format=log_format,
            enqueue=True,
        )

        # Bind experiment=None initially
        self.logger = logger.bind(experiment=self.current_experiment)

    # ------------------------------------------------------------------
    # Experiment tagging helpers
    # ------------------------------------------------------------------
    def start_experiment(self, name):
        """
        Mark all subsequent logs as belonging to a specific experiment.

        Example:
            logger.start_experiment("development")
        """
        self.current_experiment = name
        self.logger = logger.bind(experiment=name)
        self.logger.info(f"=== START EXPERIMENT: {name} ===")

    def end_experiment(self):
        """
        End the current experiment context and reset tagging.
        """
        self.logger.info(f"=== END EXPERIMENT: {self.current_experiment} ===")
        self.current_experiment = None
        self.logger = logger.bind(experiment=None)

    # ------------------------------------------------------------------
    # Decorator to log function calls
    # ------------------------------------------------------------------
    def log_call(self, func):
        """
        Decorator that logs detailed information every time a function is called.

        When applied to a method, this will automatically:
            - Log the function name and the arguments passed to it
            - Time how long the function takes to execute
            - Log the return value
            - Log any exceptions with timing information

        This is useful for debugging movement commands and tracking
        the behaviour of the autosampler over time.
        """

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
                self.logger.debug(
                    f"RETURN {func.__name__} -> {result!r} (Duration: {duration:.3f}s)"
                )
                return result

            except Exception as e:
                duration = time.time() - start_time
                self.logger.error(
                    f"EXCEPTION in {func.__name__} after {duration:.3f}s: {e}"
                )
                raise

        return wrapper

    # ------------------------------------------------------------------
    # Simple log methods
    # ------------------------------------------------------------------
    def info(self, msg):
        self.logger.info(msg)

    def debug(self, msg):
        self.logger.debug(msg)

    def error(self, msg):
        self.logger.error(msg)
