"""Logging helpers shared by command-line pipeline tasks."""

import logging


def configure_logging(level: str = "INFO") -> None:
    """Configure concise process-level logging."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
