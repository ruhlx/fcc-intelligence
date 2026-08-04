"""Structured logging setup (Stage 11).

Provides a single :func:`configure_logging` entry point and a :func:`get_logger`
helper. All pipeline stages log through the returned ``structlog`` logger so that
events (downloaded PDF, failed extraction, LLM success, duplicate merged, API
errors) are emitted as structured key/value records.
"""

from __future__ import annotations

import logging
import sys
from typing import cast

import structlog

_CONFIGURED = False


def configure_logging(level: str = "INFO", fmt: str = "console") -> None:
    """Configure standard-library logging and ``structlog``.

    :param level: Log level name, e.g. ``"INFO"`` or ``"DEBUG"``.
    :param fmt: ``"json"`` for machine-readable output, otherwise a colourised
        console renderer suitable for local development.
    """
    global _CONFIGURED

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer()
        if fmt == "json"
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structured logger, configuring logging on first use."""
    if not _CONFIGURED:
        configure_logging()
    return cast("structlog.stdlib.BoundLogger", structlog.get_logger(name))
