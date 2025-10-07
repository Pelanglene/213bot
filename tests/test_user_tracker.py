"""Tests for user tracker middleware"""

from unittest.mock import MagicMock

import pytest
from telegram import Chat

from bot.middlewares.user_tracker import UserTrackerMiddleware


@pytest.fixture
def user_tracker():
    """Create fresh user tracker instance"""
    return UserTrackerMiddleware()


@pytest.fixture
def mock_update_group():
    """Create mock Update object for group chat"""
    update = MagicMock()
    update.effective_chat.type = Chat.SUPERGROUP
    update.effective_chat.id = -100123456789
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.effective_user.is_bot = False
    return update


@pytest.fixture
def mock_update_private():
    """Create mock Update object for private chat"""
    update = MagicMock()
    update.effective_chat.type = Chat.PRIVATE
    update.effective_chat.id = 12345
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.effective_user.is_bot = False
    return update


@pytest.fixture
def mock_update_bot():
    """Create mock Update object with bot user"""
    update = MagicMock()
    update.effective_chat.type = Chat.SUPERGROUP
    update.effective_chat.id = -100123456789
    update.effective_user.id = 987654321
    update.effective_user.username = "bot_user"
    update.effective_user.is_bot = True
    return update


@pytest.fixture
def mock_context():
    """Create mock Context object"""
    context = MagicMock()
    context.chat_data = {}
    return context


@pytest.mark.asyncio
async def test_track_user_in_group(user_tracker, mock_update_group, mock_context):
    """Test tracking user in group chat"""
    await user_tracker.track_user(mock_update_group, mock_context)

    chat_id = mock_update_group.effective_chat.id
    user_id = mock_update_group.effective_user.id

    # Check internal storage
    assert user_id in user_tracker.get_recent_users(chat_id)

    # Check context.chat_data
    assert "recent_users" in mock_context.chat_data
    assert user_id in mock_context.chat_data["recent_users"]


@pytest.mark.asyncio
async def test_track_user_in_private_chat(
    user_tracker, mock_update_private, mock_context
):
    """Test that users are not tracked in private chats"""
    await user_tracker.track_user(mock_update_private, mock_context)

    chat_id = mock_update_private.effective_chat.id

    # Should not track in private chat
    assert len(user_tracker.get_recent_users(chat_id)) == 0
    assert "recent_users" not in mock_context.chat_data


@pytest.mark.asyncio
async def test_track_bot_user(user_tracker, mock_update_bot, mock_context):
    """Test that bots are not tracked"""
    await user_tracker.track_user(mock_update_bot, mock_context)

    chat_id = mock_update_bot.effective_chat.id

    # Should not track bots
    assert len(user_tracker.get_recent_users(chat_id)) == 0


@pytest.mark.asyncio
async def test_track_multiple_users(user_tracker, mock_context):
    """Test tracking multiple users in the same chat"""
    chat_id = -100123456789

    for i in range(5):
        update = MagicMock()
        update.effective_chat.type = Chat.SUPERGROUP
        update.effective_chat.id = chat_id
        update.effective_user.id = 1000 + i
        update.effective_user.is_bot = False

        await user_tracker.track_user(update, mock_context)

    # Check all users are tracked
    recent_users = user_tracker.get_recent_users(chat_id)
    assert len(recent_users) == 5
    for i in range(5):
        assert 1000 + i in recent_users


@pytest.mark.asyncio
async def test_track_same_user_multiple_times(
    user_tracker, mock_update_group, mock_context
):
    """Test that same user is not added multiple times"""
    # Track same user 3 times
    for _ in range(3):
        await user_tracker.track_user(mock_update_group, mock_context)

    chat_id = mock_update_group.effective_chat.id
    user_id = mock_update_group.effective_user.id

    recent_users = user_tracker.get_recent_users(chat_id)
    # Should only have one entry
    assert recent_users.count(user_id) == 1


@pytest.mark.asyncio
async def test_track_user_max_limit(user_tracker, mock_context):
    """Test that tracking respects MAX_RECENT_USERS limit"""
    from bot.middlewares.user_tracker import MAX_RECENT_USERS

    chat_id = -100123456789

    # Track MAX_RECENT_USERS + 10 users
    for i in range(MAX_RECENT_USERS + 10):
        update = MagicMock()
        update.effective_chat.type = Chat.SUPERGROUP
        update.effective_chat.id = chat_id
        update.effective_user.id = 2000 + i
        update.effective_user.is_bot = False

        await user_tracker.track_user(update, mock_context)

    recent_users = user_tracker.get_recent_users(chat_id)
    # Should not exceed MAX_RECENT_USERS
    assert len(recent_users) <= MAX_RECENT_USERS

    # Should have the most recent users (last MAX_RECENT_USERS)
    for i in range(10, MAX_RECENT_USERS + 10):
        assert 2000 + i in recent_users


@pytest.mark.asyncio
async def test_track_user_no_effective_chat(user_tracker, mock_context):
    """Test handling when update has no effective chat"""
    update = MagicMock()
    update.effective_chat = None
    update.effective_user = MagicMock()

    # Should not raise error
    await user_tracker.track_user(update, mock_context)


@pytest.mark.asyncio
async def test_track_user_no_effective_user(user_tracker, mock_context):
    """Test handling when update has no effective user"""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_user = None

    # Should not raise error
    await user_tracker.track_user(update, mock_context)
