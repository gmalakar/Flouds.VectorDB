import importlib
import logging

import app.logger as app_logger


def test_logger_fallback_monkeypatch(monkeypatch, capsys):
    """When RotatingFileHandler raises during setup, logger falls back to printing stderr."""
    name = "testfallback"
    full_name = f"flouds.{name}"

    # Ensure we re-create the logger (remove if previously configured)
    app_logger._configured_loggers.discard(full_name)

    # Monkeypatch the RotatingFileHandler to raise an OSError on init
    class BadHandler:
        def __init__(self, *args, **kwargs):
            raise OSError("simulated handler failure")

    monkeypatch.setattr(app_logger, "RotatingFileHandler", BadHandler)

    # Call get_logger which will attempt to create the handler and fail
    logger = app_logger.get_logger(name)

    # Capture stderr output from the failure path
    captured = capsys.readouterr()
    assert isinstance(logger, logging.Logger)
    assert "Warning: Failed to create log file handler" in captured.err
    assert "Traceback (most recent call last)" in captured.err
