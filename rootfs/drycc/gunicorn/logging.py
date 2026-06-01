import os
import logging

from gunicorn.glogging import Logger


class _ReentrantSafeStreamHandler(logging.StreamHandler):
    """
    A StreamHandler that tolerates reentrant writes to the underlying stream.

    On Python 3.14 the buffered stderr writer raises
    ``RuntimeError: reentrant call inside <_io.BufferedWriter ...>`` when a
    signal handler (e.g. gunicorn's SIGTERM/SIGCHLD handling) triggers logging
    while another log write to the same stream is already in progress. This is
    harmless noise during graceful worker shutdown, so swallow it instead of
    routing it through ``handleError`` (which itself writes to stderr and would
    raise again).
    """

    def emit(self, record):
        try:
            super().emit(record)
        except RuntimeError as exc:
            if "reentrant call" in str(exc):
                return
            raise


class Logging(Logger):
    """Gunicorn logger that quiets health checks and survives reentrant logging."""

    def setup(self, cfg):
        super().setup(cfg)
        # Replace gunicorn's error/access stream handlers with reentrant-safe ones.
        for logger in (self.error_log, self.access_log):
            for handler in list(logger.handlers):
                if isinstance(handler, logging.StreamHandler) and not isinstance(
                    handler, logging.FileHandler
                ):
                    safe_handler = _ReentrantSafeStreamHandler(handler.stream)
                    safe_handler.setFormatter(handler.formatter)
                    safe_handler.setLevel(handler.level)
                    logger.removeHandler(handler)
                    logger.addHandler(safe_handler)

    def access(self, resp, req, environ, request_time):
        # health check endpoints are only logged in debug mode
        if (
            not os.environ.get('DRYCC_DEBUG', False) and
            req.path in ['/readiness', '/healthz']
        ):
            return

        Logger.access(self, resp, req, environ, request_time)
