"""Independent verification of the priority rules (FR-11, FR-12, FR-13, FR-18).

Every expected value below was calculated BY HAND from Section 3 of
requirements-spec.md (see the test specification, "Priority formula test
oracle"). None was obtained by running the implementation, so a test can only
pass if the code really follows the specification.

Test IDs (TC-PRI-xx) match the traceability matrix in the report.
Cases where the specification is ambiguous (SPEC-GAP) accept every valid
reading and are listed as findings for the specification owner.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Difficulty as D
from app.models import PriorityLevel as L
from app.priority import (
    calculate_priority_score,
    classify_priority,
    compute_priority,
    deadline_score,
    difficulty_score,
    time_score,
)

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def due(**kw):
    return NOW + timedelta(**kw)


# --- TC-PRI-01: one value inside each deadline band -------------------------
@pytest.mark.parametrize(
    "delta, expected",
    [
        (timedelta(days=30), 10),
        (timedelta(days=10), 25),
        (timedelta(days=4), 50),
        (timedelta(hours=36), 75),
        (timedelta(hours=12), 100),
        (timedelta(hours=-1), 100),
    ],
)
def test_TC_PRI_01_deadline_score_inside_each_band(delta, expected):
    assert deadline_score(NOW + delta, NOW) == expected


# --- TC-PRI-02: band edges that every reading of the spec agrees on ----------
@pytest.mark.parametrize(
    "delta, expected",
    [
        (timedelta(seconds=-1), 100),  # just overdue
        (timedelta(0), 100),  # due right now: < 24 hours
        (timedelta(hours=23, minutes=59), 100),  # "Less than 24 hours"
        (timedelta(hours=24), 75),  # exactly 1 day: "1-2 days"
        (timedelta(hours=48), 75),  # exactly 2 days: "1-2 days"
        (timedelta(hours=72), 50),  # exactly 3 days: "3-6 days"
        (timedelta(hours=144), 50),  # exactly 6 days: "3-6 days"
        (timedelta(hours=168), 25),  # exactly 7 days: "7-14 days"
        (timedelta(hours=336), 25),  # exactly 14 days: "7-14 days"
        (timedelta(hours=336, minutes=1), 10),  # "More than 14 days"
    ],
)
def test_TC_PRI_02_deadline_band_edges(delta, expected):
    assert deadline_score(NOW + delta, NOW) == expected


# --- TC-PRI-02g: SPEC-GAP-1, times the spec's bands do not cover -------------
@pytest.mark.parametrize(
    "delta, allowed",
    [
        (timedelta(hours=49), {50, 75}),  # just over 2 days
        (timedelta(hours=60), {50, 75}),  # 2.5 days
        (timedelta(hours=71), {50, 75}),  # just under 3 days
        (timedelta(hours=145), {25, 50}),  # just over 6 days
        (timedelta(hours=156), {25, 50}),  # 6.5 days
        (timedelta(hours=167), {25, 50}),  # just under 7 days
    ],
)
def test_TC_PRI_02g_spec_gap_between_bands(delta, allowed):
    """Spec bands are '1-2 days' and '3-6 days' with nothing between them."""
    assert deadline_score(NOW + delta, NOW) in allowed


# --- TC-PRI-03 / 04: difficulty and time scores -----------------------------
@pytest.mark.parametrize(
    "difficulty, expected",
    [(D.EASY, 20), (D.MEDIUM, 50), (D.HARD, 80), (D.VERY_HARD, 100)],
)
def test_TC_PRI_03_difficulty_scores(difficulty, expected):
    assert difficulty_score(difficulty) == expected


@pytest.mark.parametrize(
    "hours, expected",
    [(0.1, 1), (0.5, 5), (1, 10), (3, 30), (5, 50), (8, 80), (9.9, 99), (10, 100), (25, 100)],
)
def test_TC_PRI_04_time_score_is_min_of_hours_times_10_and_100(hours, expected):
    assert time_score(hours) == pytest.approx(expected)


# --- TC-PRI-05: hand-calculated worked examples -----------------------------
@pytest.mark.parametrize(
    "delta, difficulty, hours, expected_score, expected_level",
    [
        (timedelta(hours=12), D.VERY_HARD, 10, 100, L.CRITICAL),  # E1: 50+30+20
        (timedelta(days=30), D.EASY, 1, 13, L.LOW),  # E2: 5+6+2
        (timedelta(days=4), D.MEDIUM, 5, 50, L.MEDIUM),  # E3: 25+15+10
        (timedelta(hours=36), D.HARD, 8, 77.5, L.HIGH),  # E4: 37.5+24+16
        (timedelta(days=10), D.VERY_HARD, 10, 62.5, L.HIGH),  # E5: 12.5+30+20
        (timedelta(days=-1), D.EASY, 1, 58, L.MEDIUM),  # E6: 50+6+2 (overdue)
    ],
)
def test_TC_PRI_05_worked_examples(delta, difficulty, hours, expected_score, expected_level):
    score, level = compute_priority(NOW + delta, difficulty, hours, NOW)
    assert score == pytest.approx(expected_score)
    assert level == expected_level


# --- TC-PRI-06: score always within 0-100 -----------------------------------
def test_TC_PRI_06_score_range_and_extremes():
    lowest = calculate_priority_score(due(days=30), D.EASY, 0.1, NOW)
    highest = calculate_priority_score(due(hours=12), D.VERY_HARD, 10, NOW)
    assert lowest == pytest.approx(11.2)
    assert highest == pytest.approx(100)
    for offset in (timedelta(days=-9), timedelta(hours=1), timedelta(days=3), timedelta(days=400)):
        for diff in D:
            for hours in (0.01, 1, 10, 1000):
                s = calculate_priority_score(NOW + offset, diff, hours, NOW)
                assert 0 <= s <= 100


# --- TC-PRI-07 / 08 / 09: classification boundaries (one input flips level) --
@pytest.mark.parametrize(
    "case, below, above",
    [
        # B1: 12 h, Medium: 7 h -> 79 / 7.5 h -> 80
        ((timedelta(hours=12), D.MEDIUM, 7, 7.5), (79, L.HIGH), (80, L.CRITICAL)),
        # B2: 4 days, Hard: 5 h -> 59 / 5.5 h -> 60
        ((timedelta(days=4), D.HARD, 5, 5.5), (59, L.MEDIUM), (60, L.HIGH)),
        # B3: 4 days, Easy: 4 h -> 39 / 4.5 h -> 40
        ((timedelta(days=4), D.EASY, 4, 4.5), (39, L.LOW), (40, L.MEDIUM)),
    ],
    ids=["TC-PRI-07", "TC-PRI-08", "TC-PRI-09"],
)
def test_TC_PRI_07_08_09_classification_boundaries(case, below, above):
    delta, diff, hours_below, hours_above = case
    s1, l1 = compute_priority(NOW + delta, diff, hours_below, NOW)
    s2, l2 = compute_priority(NOW + delta, diff, hours_above, NOW)
    assert s1 == pytest.approx(below[0]) and l1 == below[1]
    assert s2 == pytest.approx(above[0]) and l2 == above[1]


@pytest.mark.parametrize(
    "score, level",
    [(0, L.LOW), (39, L.LOW), (40, L.MEDIUM), (59, L.MEDIUM),
     (60, L.HIGH), (79, L.HIGH), (80, L.CRITICAL), (100, L.CRITICAL)],
)
def test_TC_PRI_07_classify_whole_number_scores(score, level):
    assert classify_priority(score) == level


def test_TC_PRI_10_spec_gap_decimal_score_between_79_and_80():
    """SPEC-GAP-2: 79.8 is in neither '60-79' nor '80-100'."""
    score, level = compute_priority(due(hours=12), D.MEDIUM, 7.4, NOW)  # 50+15+14.8
    assert score == pytest.approx(79.8)
    assert level in {L.HIGH, L.CRITICAL}


# --- TC-PRI-14: urgency rises as time passes --------------------------------
def test_TC_PRI_14_score_changes_as_the_deadline_approaches():
    deadline = NOW + timedelta(days=4)
    early, _ = compute_priority(deadline, D.MEDIUM, 5, NOW)
    later, _ = compute_priority(deadline, D.MEDIUM, 5, NOW + timedelta(days=3, hours=12))
    assert early == pytest.approx(50)  # 25 + 15 + 10
    assert later == pytest.approx(75)  # 50 + 15 + 10 (12 h left -> deadline score 100)
