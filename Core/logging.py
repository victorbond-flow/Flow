"""
Central logging singleton for the entire project.

All modules should import:
    from Core.logging import flow_logger as logger, log_call

Only entry-point code (e.g. notebooks, scripts) should call:
    logger.start_experiment(...)
"""

from .flow_logging import FlowLogger

# ------------------------------------------------------------------
# Create the ONE global logger instance
# ------------------------------------------------------------------

flow_logger = FlowLogger()

# Convenience alias for decorator usage
log_call = flow_logger.log_call
