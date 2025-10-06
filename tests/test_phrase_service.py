"""Tests for PhraseService"""

import json
from pathlib import Path

import pytest

from bot.services.phrase_service import PhraseService


@pytest.fixture
def temp_phrases_file(tmp_path):
    """Create temporary phrases file"""
    phrases_file = tmp_path / "phrases.json"
    data = {"phrases": ["Test phrase 1", "Test phrase 2", "Test phrase 3"]}
    phrases_file.write_text(json.dumps(data), encoding="utf-8")
    return phrases_file


def test_load_phrases(temp_phrases_file):
    """Test loading phrases from file"""
    service = PhraseService(temp_phrases_file)
    phrases = service.get_all_phrases()

    assert len(phrases) == 3
    assert "Test phrase 1" in phrases
    assert "Test phrase 2" in phrases
    assert "Test phrase 3" in phrases


def test_get_random_phrase(temp_phrases_file):
    """Test getting random phrase"""
    service = PhraseService(temp_phrases_file)
    phrase = service.get_random_phrase()

    assert phrase is not None
    assert phrase in service.get_all_phrases()


def test_missing_file():
    """Test handling missing file"""
    service = PhraseService(Path("nonexistent.json"))
    phrases = service.get_all_phrases()

    assert len(phrases) == 1
    assert phrases[0] == "Pong!"


def test_reload_phrases(temp_phrases_file):
    """Test reloading phrases"""
    service = PhraseService(temp_phrases_file)

    # Modify file
    new_data = {"phrases": ["New phrase"]}
    temp_phrases_file.write_text(json.dumps(new_data), encoding="utf-8")

    # Reload
    service.reload_phrases()
    phrases = service.get_all_phrases()

    assert len(phrases) == 1
    assert phrases[0] == "New phrase"
