"""Tests for RateLimiter"""

from time import sleep

import pytest

from bot.middlewares.rate_limit import RateLimiter


def test_rate_limiter_allows_first_request():
    """Test that first request is always allowed"""
    limiter = RateLimiter(cooldown_seconds=1.0)
    assert limiter.is_allowed(123) is True


def test_rate_limiter_blocks_rapid_requests():
    """Test that rapid requests are blocked"""
    limiter = RateLimiter(cooldown_seconds=1.0)

    # First request allowed
    assert limiter.is_allowed(123) is True

    # Immediate second request blocked
    assert limiter.is_allowed(123) is False


def test_rate_limiter_allows_after_cooldown():
    """Test that requests are allowed after cooldown"""
    limiter = RateLimiter(cooldown_seconds=0.1)

    # First request
    assert limiter.is_allowed(123) is True

    # Immediate second request blocked
    assert limiter.is_allowed(123) is False

    # Wait for cooldown
    sleep(0.15)

    # Should be allowed now
    assert limiter.is_allowed(123) is True


def test_rate_limiter_different_users():
    """Test that different users have separate limits"""
    limiter = RateLimiter(cooldown_seconds=1.0)

    # User 1
    assert limiter.is_allowed(111) is True
    assert limiter.is_allowed(111) is False

    # User 2 (should be allowed)
    assert limiter.is_allowed(222) is True
    assert limiter.is_allowed(222) is False


def test_get_remaining_cooldown():
    """Test getting remaining cooldown time"""
    limiter = RateLimiter(cooldown_seconds=1.0)

    # No cooldown for new user
    assert limiter.get_remaining_cooldown(123) == 0.0

    # After first request
    limiter.is_allowed(123)
    remaining = limiter.get_remaining_cooldown(123)
    assert 0.0 < remaining <= 1.0


def test_reset_user():
    """Test resetting user cooldown"""
    limiter = RateLimiter(cooldown_seconds=1.0)

    # Make request
    assert limiter.is_allowed(123) is True
    assert limiter.is_allowed(123) is False

    # Reset
    limiter.reset_user(123)

    # Should be allowed again
    assert limiter.is_allowed(123) is True
