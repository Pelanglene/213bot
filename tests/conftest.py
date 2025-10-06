"""Pytest configuration and fixtures"""

import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env():
    """Set test environment variables"""
    os.environ["BOT_TOKEN"] = "test_token_123"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["DEBUG"] = "true"
