"""Tests for kill_random handler"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Chat, ChatMember
from telegram.error import TelegramError

from bot.handlers.kill_random import kill_random_command


@pytest.fixture
def mock_update_group():
    """Create mock Update object for group chat"""
    update = MagicMock()
    update.effective_chat.type = Chat.SUPERGROUP
    update.effective_chat.id = -100123456789
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.message.message_id = 999
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_update_private():
    """Create mock Update object for private chat"""
    update = MagicMock()
    update.effective_chat.type = Chat.PRIVATE
    update.effective_chat.id = 12345
    update.effective_user.id = 12345
    update.effective_user.username = "test_user"
    update.message.message_id = 999
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Context object"""
    context = MagicMock()
    context.bot.id = 987654321
    context.chat_data = {"recent_users": [111, 222, 333, 444, 555]}
    return context


@pytest.mark.asyncio
async def test_kill_random_private_chat(mock_update_private, mock_context):
    """Test that command fails in private chat"""
    await kill_random_command(mock_update_private, mock_context)

    mock_update_private.message.reply_text.assert_called_once()
    call_args = mock_update_private.message.reply_text.call_args
    assert "только в групповых чатах" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_bot_not_admin(mock_update_group, mock_context):
    """Test that command fails when bot is not admin"""
    # Mock bot member as regular member
    bot_member = MagicMock()
    bot_member.status = ChatMember.MEMBER

    mock_update_group.effective_chat.get_member = AsyncMock(return_value=bot_member)

    await kill_random_command(mock_update_group, mock_context)

    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "прав администратора" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_bot_cant_restrict(mock_update_group, mock_context):
    """Test that command fails when bot can't restrict members"""
    # Mock bot member as admin without restrict permission
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = False

    mock_update_group.effective_chat.get_member = AsyncMock(return_value=bot_member)

    await kill_random_command(mock_update_group, mock_context)

    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "ограничивать участников" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_too_few_members(mock_update_group, mock_context):
    """Test that command fails when chat has too few members"""
    # Mock bot member as admin with permissions
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = True

    mock_update_group.effective_chat.get_member = AsyncMock(return_value=bot_member)
    mock_update_group.effective_chat.get_member_count = AsyncMock(return_value=2)

    await kill_random_command(mock_update_group, mock_context)

    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "недостаточно участников" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_no_recent_users(mock_update_group, mock_context):
    """Test that command fails when no recent users are tracked"""
    # Mock bot member as admin with permissions
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = True

    mock_update_group.effective_chat.get_member = AsyncMock(return_value=bot_member)
    mock_update_group.effective_chat.get_member_count = AsyncMock(return_value=10)
    mock_update_group.effective_chat.get_administrators = AsyncMock(return_value=[])

    # No recent users
    mock_context.chat_data = {}

    await kill_random_command(mock_update_group, mock_context)

    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "Не могу найти участников" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_success(mock_update_group, mock_context):
    """Test successful kick of random user"""
    # Mock bot member as admin with permissions
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = True

    # Mock user member as admin (to bypass cooldown)
    user_member = MagicMock()
    user_member.status = ChatMember.ADMINISTRATOR

    # Mock target user
    target_member = MagicMock()
    target_member.user.id = 222
    target_member.user.full_name = "Target User"
    target_member.user.username = "target_user"

    async def get_member_side_effect(user_id):
        if user_id == mock_context.bot.id:
            return bot_member
        if user_id == mock_update_group.effective_user.id:
            return user_member
        return target_member

    mock_update_group.effective_chat.get_member = AsyncMock(
        side_effect=get_member_side_effect
    )
    mock_update_group.effective_chat.get_member_count = AsyncMock(return_value=10)
    mock_update_group.effective_chat.get_administrators = AsyncMock(
        return_value=[bot_member]
    )
    mock_update_group.effective_chat.ban_member = AsyncMock()
    mock_update_group.effective_chat.unban_member = AsyncMock()

    with patch("bot.handlers.kill_random.random.choice", return_value=222):
        await kill_random_command(mock_update_group, mock_context)

    # Check that ban and unban were called
    mock_update_group.effective_chat.ban_member.assert_called_once_with(222)
    mock_update_group.effective_chat.unban_member.assert_called_once_with(222)

    # Check response message
    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "Рулетка выбрала жертву" in call_args[0][0]
    assert "@target_user" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_telegram_error(mock_update_group, mock_context):
    """Test handling of Telegram API errors"""
    # Mock bot member as admin with permissions
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = True

    # Mock user member as admin (to bypass cooldown)
    user_member = MagicMock()
    user_member.status = ChatMember.ADMINISTRATOR

    target_member = MagicMock()
    target_member.user.id = 222
    target_member.user.full_name = "Target User"
    target_member.user.username = None

    async def get_member_side_effect(user_id):
        if user_id == mock_context.bot.id:
            return bot_member
        if user_id == mock_update_group.effective_user.id:
            return user_member
        return target_member

    mock_update_group.effective_chat.get_member = AsyncMock(
        side_effect=get_member_side_effect
    )
    mock_update_group.effective_chat.get_member_count = AsyncMock(return_value=10)
    mock_update_group.effective_chat.get_administrators = AsyncMock(
        return_value=[bot_member]
    )
    mock_update_group.effective_chat.ban_member = AsyncMock(
        side_effect=TelegramError("Test error")
    )

    with patch("bot.handlers.kill_random.random.choice", return_value=222):
        await kill_random_command(mock_update_group, mock_context)

    # Check error message
    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "Ошибка при попытке кика" in call_args[0][0]


@pytest.mark.asyncio
async def test_kill_random_cooldown_for_regular_user(mock_update_group, mock_context):
    """Test that regular users are blocked by cooldown"""
    from bot.middlewares.command_cooldown import cooldown_service

    # Mark command as already used
    cooldown_service.mark_used("kill_random")

    # Mock user member as regular member (not admin)
    user_member = MagicMock()
    user_member.status = ChatMember.MEMBER

    mock_update_group.effective_chat.get_member = AsyncMock(return_value=user_member)

    await kill_random_command(mock_update_group, mock_context)

    # Check that cooldown message was sent
    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "уже использовалась сегодня" in call_args[0][0]

    # Clean up
    cooldown_service._last_used.clear()


@pytest.mark.asyncio
async def test_kill_random_admin_bypass_cooldown(mock_update_group, mock_context):
    """Test that admins can bypass cooldown"""
    from bot.middlewares.command_cooldown import cooldown_service

    # Mark command as already used
    cooldown_service.mark_used("kill_random")

    # Mock bot member as admin
    bot_member = MagicMock()
    bot_member.status = ChatMember.ADMINISTRATOR
    bot_member.can_restrict_members = True

    # Mock user member as admin
    user_member = MagicMock()
    user_member.status = ChatMember.ADMINISTRATOR

    # Mock target user
    target_member = MagicMock()
    target_member.user.id = 333
    target_member.user.full_name = "Target User"
    target_member.user.username = "target"

    async def get_member_side_effect(user_id):
        if user_id == mock_context.bot.id:
            return bot_member
        if user_id == mock_update_group.effective_user.id:
            return user_member
        return target_member

    mock_update_group.effective_chat.get_member = AsyncMock(
        side_effect=get_member_side_effect
    )
    mock_update_group.effective_chat.get_member_count = AsyncMock(return_value=10)
    mock_update_group.effective_chat.get_administrators = AsyncMock(
        return_value=[bot_member]
    )
    mock_update_group.effective_chat.ban_member = AsyncMock()
    mock_update_group.effective_chat.unban_member = AsyncMock()

    with patch("bot.handlers.kill_random.random.choice", return_value=333):
        await kill_random_command(mock_update_group, mock_context)

    # Check that command executed successfully (no cooldown message)
    mock_update_group.message.reply_text.assert_called_once()
    call_args = mock_update_group.message.reply_text.call_args
    assert "Рулетка выбрала жертву" in call_args[0][0]

    # Clean up
    cooldown_service._last_used.clear()
