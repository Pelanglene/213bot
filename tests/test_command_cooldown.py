"""Tests for command cooldown service"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from bot.middlewares.command_cooldown import CommandCooldownService, format_timedelta


@pytest.fixture
def service():
    """Create CommandCooldownService instance"""
    return CommandCooldownService()


def test_can_execute_no_history(service):
    """Test that command can be executed when no history exists"""
    can_execute, remaining = service.can_execute("test_command")
    assert can_execute is True
    assert remaining is None


def test_can_execute_after_cooldown(service):
    """Test that command can be executed after cooldown expires"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    service._last_used["test_command"] = datetime.now(moscow_tz) - timedelta(hours=25)

    can_execute, remaining = service.can_execute("test_command", cooldown_hours=24)
    assert can_execute is True
    assert remaining is None


def test_cannot_execute_during_cooldown(service):
    """Test that command cannot be executed during cooldown"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    service._last_used["test_command"] = datetime.now(moscow_tz) - timedelta(hours=1)

    can_execute, remaining = service.can_execute("test_command", cooldown_hours=24)
    assert can_execute is False
    assert remaining is not None
    assert remaining.total_seconds() > 0


def test_mark_used(service):
    """Test marking command as used"""
    service.mark_used("test_command")
    assert "test_command" in service._last_used


def test_mark_used_updates_timestamp(service):
    """Test that mark_used updates the timestamp"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    old_time = datetime.now(moscow_tz) - timedelta(hours=2)
    service._last_used["test_command"] = old_time

    service.mark_used("test_command")
    assert service._last_used["test_command"] > old_time


def test_get_remaining_cooldown_no_history(service):
    """Test getting remaining cooldown when no history exists"""
    remaining = service.get_remaining_cooldown("test_command")
    assert remaining is None


def test_get_remaining_cooldown_during_cooldown(service):
    """Test getting remaining cooldown during active cooldown"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    service._last_used["test_command"] = datetime.now(moscow_tz) - timedelta(hours=1)

    remaining = service.get_remaining_cooldown("test_command", cooldown_hours=24)
    assert remaining is not None
    # Should have approximately 23 hours remaining
    assert 22 * 3600 < remaining.total_seconds() < 24 * 3600


def test_multiple_commands_independent(service):
    """Test that different commands have independent cooldowns"""
    service.mark_used("command1")

    can_execute1, _ = service.can_execute("command1", cooldown_hours=24)
    can_execute2, _ = service.can_execute("command2", cooldown_hours=24)

    assert can_execute1 is False  # command1 is on cooldown
    assert can_execute2 is True  # command2 has no history


def test_format_timedelta_hours_and_minutes():
    """Test formatting timedelta with hours and minutes"""
    td = timedelta(hours=23, minutes=45)
    result = format_timedelta(td)
    assert result == "23ч 45м"


def test_format_timedelta_only_minutes():
    """Test formatting timedelta with only minutes"""
    td = timedelta(minutes=30)
    result = format_timedelta(td)
    assert result == "30м"


def test_format_timedelta_zero_minutes():
    """Test formatting timedelta with zero minutes"""
    td = timedelta(hours=5, minutes=0)
    result = format_timedelta(td)
    assert result == "5ч 0м"


def test_format_timedelta_less_than_minute():
    """Test formatting timedelta less than a minute"""
    td = timedelta(seconds=30)
    result = format_timedelta(td)
    assert result == "0м"


def test_custom_cooldown_hours(service):
    """Test using custom cooldown period"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    service._last_used["test_command"] = datetime.now(moscow_tz) - timedelta(hours=2)

    # With 1 hour cooldown, should be executable
    can_execute, remaining = service.can_execute("test_command", cooldown_hours=1)
    assert can_execute is True
    assert remaining is None

    # With 3 hour cooldown, should not be executable
    can_execute, remaining = service.can_execute("test_command", cooldown_hours=3)
    assert can_execute is False
    assert remaining is not None
