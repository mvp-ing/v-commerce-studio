#!/usr/bin/env python
#
# Logging utility for Cart Service

import logging
import sys
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = record.created
        if log_record.get('severity'):
            log_record['severity'] = log_record['severity'].upper()
        else:
            log_record['severity'] = record.levelname


def getJSONLogger(name):
    """Create and return a JSON-formatted logger."""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter('%(timestamp)s %(severity)s %(name)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger
