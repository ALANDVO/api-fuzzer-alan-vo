"""Celery tasks for distributed fuzz execution."""
from typing import Any, Dict
import json
from backend.app.services.fuzz_runner import execute_fuzz_case_celery

# The actual task function is imported from fuzz_runner;
# this file just ensures auto-discovery finds the module.
