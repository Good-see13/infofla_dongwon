"""
GUI lifecycle helpers.

Responsible for launching and terminating the PySide6 GUI
alongside the FastAPI service.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


logger = logging.getLogger("webcam.events.gui")

_gui_process: Optional[subprocess.Popen] = None
GUI_ENABLED = os.getenv("ENABLE_GUI", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
    "",
)

# Project root (= location of webcam.py)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
GUI_SCRIPT = PROJECT_ROOT / "webcam.py"


def start_gui(custom_logger: Optional[logging.Logger] = None):
    """Launch GUI process if enabled and not already running."""
    global _gui_process
    log = custom_logger or logger

    if not GUI_ENABLED:
        log.info("GUI launch skipped (ENABLE_GUI=false)")
        return

    if _gui_process and _gui_process.poll() is None:
        log.info("GUI process already running (pid=%s)", _gui_process.pid)
        return

    if not GUI_SCRIPT.exists():
        log.warning("GUI script not found: %s", GUI_SCRIPT)
        return

    try:
        _gui_process = subprocess.Popen(
            [sys.executable, str(GUI_SCRIPT)],
            env=os.environ.copy(),
        )
        log.info("GUI process started (pid=%s)", _gui_process.pid)
    except Exception as exc:  # pragma: no cover - defensive
        _gui_process = None
        log.error("GUI launch failed: %s", exc)


def stop_gui(custom_logger: Optional[logging.Logger] = None):
    """Terminate GUI process if running."""
    global _gui_process
    log = custom_logger or logger

    if _gui_process is None:
        return

    if _gui_process.poll() is None:
        log.info("Stopping GUI process (pid=%s)", _gui_process.pid)
        _gui_process.terminate()
        try:
            _gui_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("GUI process unresponsive; killing...")
            _gui_process.kill()
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("GUI termination error: %s", exc)

    _gui_process = None
