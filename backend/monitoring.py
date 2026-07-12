"""Monitoring, logging, and error tracking setup."""
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Structured logging with error tracking."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Configure file and console handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler
        log_dir = "/logs"
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(f"{log_dir}/maritime-studio.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        self.logger.setLevel(logging.DEBUG)

    def log_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None):
        """Log structured event."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'message': message,
        }
        if data:
            event.update(data)
        self.logger.info(f"EVENT: {event}")

    def log_error(self, error_type: str, message: str, exception: Optional[Exception] = None):
        """Log structured error."""
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': error_type,
            'message': message,
        }
        if exception:
            error_data['exception'] = str(exception)
            error_data['exc_type'] = type(exception).__name__
        self.logger.error(f"ERROR: {error_data}", exc_info=exception)

    def log_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Log metric."""
        metric = {
            'timestamp': datetime.utcnow().isoformat(),
            'metric': metric_name,
            'value': value,
        }
        if tags:
            metric['tags'] = tags
        self.logger.info(f"METRIC: {metric}")


# Global logger instance
app_logger = StructuredLogger(__name__)


def setup_monitoring():
    """Initialize all monitoring systems."""
    app_logger.log_event(
        'system_startup',
        'Monitoring system initialized',
        {
            'version': '1.0.0',
            'environment': os.getenv('ENVIRONMENT', 'development'),
        }
    )
