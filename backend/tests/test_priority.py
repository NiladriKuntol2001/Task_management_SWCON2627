"""Unit tests for the priority formula — Section 3 of requirements-spec.md.

These pin down the exact numbers from the spec so any accidental change to
the formula (weights, thresholds, classification bands) is caught immediately.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Difficulty, PriorityLevel
from app.priority import (
    calculate_priority_score,
    classify_priority,
    deadline_score,
    difficulty_score,
    time_score,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    "delta,expected",
    [
        (timedelta(days=30), 10),   # more than 14 days
        (timedelta(days=15), 10),   # just over 14 days
        (timedelta(days=14), 25),   # 7-14 days (upper bound)
        (timedelta(days=7), 25),    # 7-14 days (lower bound)
        (timedelta(days=6), 50),    # 3-6 days
        (timedelta(days=3), 50),    # 3-6 days (lower bound)
        (timedelta(days=2), 75),    # 1-2 days
        (timedelta(days=1), 75),    # 1-2 days (lower bound)
        (timedelta(hours=23), 100),  # less than 24 hours
        (timedelta(hours=1), 100),
        (timedelta(hours=-5), 100),  # overdue
        (timedelta(days=-3), 100),  # overdue
    ],
)
def test_deadline_score_bands(delta, expected):
    assert deadline_score(NOW + delta, now=NOW) == expected


@pytest.mark.parametrize(
    "difficulty,expected",
    [
        (Difficulty.EASY, 20),
        (Difficulty.MEDIUM, 50),
        (Difficulty.HARD, 80),
        (Difficulty.VERY_HARD, 100),
    ],
)
def test_difficulty_score(difficulty, expected):
    assert difficulty_score(difficulty) == expected


@pytest.mark.parametrize(
    "hours,expected",
    [
        (1, 10),
        (3, 30),
        (5, 50),
        (8, 80),
        (10, 100),
        (15, 100),  # capped at 100
        (0.5, 5),
    ],
)
def test_time_score(hours, expected):
    assert time_score(hours) == expected


def test_calculate_priority_score_weighted_combination():
    # deadline in 5 days -> 50, Hard -> 80, 5 hours -> 50
    # 50*0.5 + 80*0.3 + 50*0.2 = 25 + 24 + 10 = 59
    score = calculate_priority_score(
        NOW + timedelta(days=5), Difficulty.HARD, 5, now=NOW
    )
    assert score == 59


def test_calculate_priority_score_overdue_very_hard_long_task():
    # overdue -> 100, Very Hard -> 100, 12 hours -> 100 (capped)
    # 100*0.5 + 100*0.3 + 100*0.2 = 100
    score = calculate_priority_score(
        NOW - timedelta(days=1), Difficulty.VERY_HARD, 12, now=NOW
    )
    assert score == 100


@pytest.mark.parametrize(
    "score,expected",
    [
        (100, PriorityLevel.CRITICAL),
        (80, PriorityLevel.CRITICAL),
        (79.9, PriorityLevel.HIGH),
        (60, PriorityLevel.HIGH),
        (59.9, PriorityLevel.MEDIUM),
        (40, PriorityLevel.MEDIUM),
        (39.9, PriorityLevel.LOW),
        (0, PriorityLevel.LOW),
    ],
)
def test_classify_priority_bands(score, expected):
    assert classify_priority(score) == expected
