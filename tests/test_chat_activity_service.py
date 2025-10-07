"""Tests for chat activity service"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from bot.services.chat_activity_service import ChatActivityService


@pytest.fixture
def service():
    """Create ChatActivityService instance"""
    return ChatActivityService()


def test_update_activity(service):
    """Test updating chat activity"""
    chat_id = 123
    service.update_activity(chat_id)

    assert chat_id in service._last_activity


def test_is_chat_inactive_no_activity(service):
    """Test that chat with no activity is not inactive"""
    chat_id = 123
    assert not service.is_chat_inactive(chat_id)


def test_is_chat_inactive_recent_activity(service):
    """Test that chat with recent activity is not inactive"""
    chat_id = 123
    service.update_activity(chat_id)

    assert not service.is_chat_inactive(chat_id)


def test_is_chat_inactive_old_activity(service):
    """Test that chat with old activity is inactive during active hours"""
    chat_id = 123
    moscow_tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(moscow_tz)

    # Set activity to 16 minutes ago from now
    old_active_time = now - timedelta(minutes=16)
    service._last_activity[chat_id] = old_active_time

    # If current hour is between 9 and 21, should be inactive
    if 9 <= now.hour < 21:
        assert service.is_chat_inactive(chat_id)
    else:
        # Outside active hours, should not be inactive
        assert not service.is_chat_inactive(chat_id)


def test_is_active_hours(service):
    """Test active hours detection"""
    moscow_tz = ZoneInfo("Europe/Moscow")

    # Test active hour (12:00)
    active_dt = datetime.now(moscow_tz).replace(hour=12, minute=0)
    assert service._is_active_hours(active_dt)

    # Test edge case - 9:00 (should be active)
    edge_start = datetime.now(moscow_tz).replace(hour=9, minute=0)
    assert service._is_active_hours(edge_start)

    # Test edge case - 21:00 (should be inactive)
    edge_end = datetime.now(moscow_tz).replace(hour=21, minute=0)
    assert not service._is_active_hours(edge_end)

    # Test inactive hour (22:00)
    inactive_dt = datetime.now(moscow_tz).replace(hour=22, minute=0)
    assert not service._is_active_hours(inactive_dt)

    # Test early morning (6:00)
    early_dt = datetime.now(moscow_tz).replace(hour=6, minute=0)
    assert not service._is_active_hours(early_dt)


def test_get_inactive_chats(service):
    """Test getting list of inactive chats"""
    moscow_tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(moscow_tz)

    # Create active hour time
    if 9 <= now.hour < 21:
        # We're in active hours, use current time
        base_time = now
    else:
        # Outside active hours, use 12:00 today
        base_time = now.replace(hour=12, minute=0, second=0, microsecond=0)

    # Active chat
    chat_id_1 = 123
    service._last_activity[chat_id_1] = base_time

    # Inactive chat (16 minutes ago)
    chat_id_2 = 456
    service._last_activity[chat_id_2] = base_time - timedelta(minutes=16)

    # Another inactive chat (20 minutes ago)
    chat_id_3 = 789
    service._last_activity[chat_id_3] = base_time - timedelta(minutes=20)

    inactive = service.get_inactive_chats()

    # Both chat_id_2 and chat_id_3 should be in the list if we're in active hours
    if 9 <= now.hour < 21:
        assert chat_id_2 in inactive
        assert chat_id_3 in inactive
        assert chat_id_1 not in inactive
    else:
        # Outside active hours, no chats should be inactive
        assert len(inactive) == 0


def test_mark_dead_chat_sent(service):
    """Test marking dead chat as sent updates activity time"""
    chat_id = 123
    moscow_tz = ZoneInfo("Europe/Moscow")

    # Set old activity
    old_time = datetime.now(moscow_tz) - timedelta(minutes=20)
    service._last_activity[chat_id] = old_time

    # Mark as sent
    service.mark_dead_chat_sent(chat_id)

    # Should update activity time to now
    assert service._last_activity[chat_id] > old_time


def test_repeated_dead_chat_messages(service):
    """Test that dead chat messages continue to be sent every 15 minutes"""
    chat_id = 123
    moscow_tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(moscow_tz)

    # Set activity to 16 minutes ago from now
    service._last_activity[chat_id] = now - timedelta(minutes=16)

    # Should be inactive during active hours
    if 9 <= now.hour < 21:
        assert service.is_chat_inactive(chat_id)

    # Mark as sent - updates activity
    service.mark_dead_chat_sent(chat_id)

    # Now should NOT be inactive
    assert not service.is_chat_inactive(chat_id)

    # But if we wait another 16 minutes (simulate), should be inactive again
    service._last_activity[chat_id] = now - timedelta(minutes=16)
    if 9 <= now.hour < 21:
        assert service.is_chat_inactive(chat_id)


def test_custom_inactive_threshold():
    """Test that custom inactive threshold can be set"""
    # Create service with custom 5 minute threshold
    service = ChatActivityService(inactive_minutes=5)
    chat_id = 123
    moscow_tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(moscow_tz)

    # Set activity to 6 minutes ago from now
    service._last_activity[chat_id] = now - timedelta(minutes=6)

    # Should be inactive with 5 minute threshold during active hours
    if 9 <= now.hour < 21:
        assert service.is_chat_inactive(chat_id)

    # Set activity to 4 minutes ago from now
    service._last_activity[chat_id] = now - timedelta(minutes=4)

    # Should NOT be inactive with 5 minute threshold
    assert not service.is_chat_inactive(chat_id)
