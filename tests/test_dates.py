"""Date cells from real outlines resolve to the stated day, month, year and time (D2)."""
from datetime import date, time

import pytest

from src.outline.dates import DateResolver


def winter():
    return DateResolver(term_start=date(2026, 1, 5), term_end=date(2026, 4, 9),
                        exam_periods=[(date(2026, 4, 12), date(2026, 4, 30))])


def fall():
    return DateResolver(term_start=date(2025, 9, 4), term_end=date(2025, 12, 9),
                        exam_periods=[(date(2025, 12, 11), date(2025, 12, 22))],
                        reading_weeks=[(date(2025, 11, 3), date(2025, 11, 9))])


def full_year():
    return DateResolver(term_start=date(2025, 9, 4), term_end=date(2026, 4, 9),
                        exam_periods=[(date(2025, 12, 11), date(2025, 12, 22)),
                                      (date(2026, 4, 12), date(2026, 4, 30))])


@pytest.mark.parametrize("text, expected", [
    ("Jan 16th", date(2026, 1, 16)),                       # KIN 2000 table cell
    ("Feb 12th", date(2026, 2, 12)),
    ("Thursday, January 29", date(2026, 1, 29)),           # CS 3340B
    ("25 February 2026", date(2026, 2, 25)),               # Classical Studies 1000
])
def test_winter_dates(text, expected):
    r = winter().resolve(text)
    assert r.status == "exact"
    assert r.date == expected


@pytest.mark.parametrize("text, expected_date, expected_time", [
    ("Nov.29th", date(2025, 11, 29), None),                              # ECE 2240A
    ("Oct. 9", date(2025, 10, 9), None),                                 # CS 3342A inline
    ("Wed. December 8th.", date(2025, 12, 8), None),                     # Biochem
    ("Due Monday September 29", date(2025, 9, 29), None),
    ("Thursday, Oct. 30, 11:30 - 1:30pm", date(2025, 10, 30), time(11, 30)),
    ("Covers Chapter 1. Friday Oct. 3 7-8:30pm", date(2025, 10, 3), time(19, 0)),  # Math 1228
    ("November 14th 6 – 8 PM", date(2025, 11, 14), time(18, 0)),        # Physiology
    ("December 8th by 11:59\nPM.", date(2025, 12, 8), time(23, 59)),
    ("12 November 2025", date(2025, 11, 12), None),
])
def test_fall_dates(text, expected_date, expected_time):
    r = fall().resolve(text)
    assert r.status == "exact", r
    assert r.date == expected_date
    assert r.time == expected_time


def test_full_year_picks_the_year_from_the_month():
    r = full_year()
    assert r.resolve("Author: Mon, Oct. 27th\nby 11:59 PM.\nAnswer and provide\nfeedback: Wed, Oct.\n29th by 11:59 PM.").date == date(2025, 10, 27)
    assert r.resolve("Author: Mon, Jan. 19th by 11:59 PM.").date == date(2026, 1, 19)
    assert r.resolve("Wed, Apr 8th by 11:59 PM.").date == date(2026, 4, 8)
    assert r.resolve("October 16").date == date(2025, 10, 16)
    assert r.resolve("February 5").date == date(2026, 2, 5)


def test_weekday_disambiguates_the_year_when_the_term_is_unknown():
    r = DateResolver(term_start=None, term_end=None, exam_periods=[], year_hints=[2025, 2026])
    assert r.resolve("Friday Oct. 3").date == date(2025, 10, 3)      # Oct 3 2025 is a Friday
    assert r.resolve("Friday Nov. 14").date == date(2025, 11, 14)


def test_weekday_mismatch_keeps_the_date_as_written():
    r = fall().resolve("Due Wednesday October 13")  # Oct 13 2025 is a Monday; keep the printed date
    assert r.date == date(2025, 10, 13)


@pytest.mark.parametrize("text, status", [
    ("Registrar", "registrar"),
    ("TBD by\nRegistrar", "registrar"),
    ("Date TBD- scheduled by\nthe registrar", "registrar"),
    ("Scheduled by the Registrar", "registrar"),
    ("The date will be published by the registrar.", "registrar"),
    ("Final exam period", "registrar"),
    ("Date TBA", "tba"),
    ("TBA", "tba"),
    ("", "missing"),
    ("Only the best 5 of the 6 quizzes count", "missing"),
])
def test_undated_cells_get_a_status_not_a_date(text, status):
    r = fall().resolve(text)
    assert r.status == status
    assert r.date is None


def test_registrar_carries_the_exam_period_window():
    r = winter().resolve("Registrar")
    assert r.window == (date(2026, 4, 12), date(2026, 4, 30))


def test_exam_period_phrases_are_ranges():
    r = full_year().resolve("during December exam period")
    assert r.status == "range"
    assert r.window == (date(2025, 12, 11), date(2025, 12, 22))
    r2 = full_year().resolve("Final exam period")
    assert r2.status == "registrar"
    assert r2.window == (date(2026, 4, 12), date(2026, 4, 30))


def test_relative_rules_are_rules():
    r = fall().resolve("Lab Report\ndue 24hrs\nafter each\nLab Session")
    assert r.status == "rule"
    assert r.date is None


def test_recurring_weekly_span():
    r = fall().resolve("Each Friday of a lecture week (starting Sept 12 and ending November 14) you will have a quiz")
    assert r.status == "recurring"
    assert r.dates[0] == date(2025, 9, 12)
    assert r.dates[-1] == date(2025, 11, 14)
    assert all(d.weekday() == 4 for d in r.dates)
    assert date(2025, 11, 7) not in r.dates  # reading week


def test_two_dates_in_a_cell_use_the_first_and_keep_the_second():
    r = full_year().resolve("Author: Mon, Oct. 27th by 11:59 PM. Answer and provide feedback: Wed, Oct. 29th by 11:59 PM.")
    assert r.date == date(2025, 10, 27)
    assert r.time == time(23, 59)
    assert r.secondary_date == date(2025, 10, 29)
