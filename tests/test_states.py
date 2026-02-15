"""
Тесты для backend.bot.handlers.states (константы состояний).
"""
import pytest

from backend.bot.handlers.states import (
    SELECTING_LANDING_TYPE,
    COLLECTING_PRODUCT_NAME,
    COLLECTING_HERO_MEDIA,
    COLLECTING_PRICES,
    COLLECTING_DESCRIPTION,
    COLLECTING_FOOTER_INFO,
    CONFIRMING,
    GENERATING,
)


class TestStates:
    """Константы состояний — целые числа 0..15, уникальные."""

    def test_states_are_integers(self):
        assert isinstance(SELECTING_LANDING_TYPE, int)
        assert isinstance(COLLECTING_PRODUCT_NAME, int)
        assert isinstance(GENERATING, int)

    def test_states_range(self):
        assert SELECTING_LANDING_TYPE >= 0
        assert GENERATING < 16

    def test_states_unique(self):
        states = [
            SELECTING_LANDING_TYPE,
            COLLECTING_PRODUCT_NAME,
            COLLECTING_HERO_MEDIA,
            COLLECTING_PRICES,
            COLLECTING_DESCRIPTION,
            COLLECTING_FOOTER_INFO,
            CONFIRMING,
            GENERATING,
        ]
        assert len(states) == len(set(states))

    def test_confirming_before_generating(self):
        assert CONFIRMING < GENERATING
