"""Unit tests for caching system."""

import pytest
import tempfile
from pathlib import Path
from src.cache import CacheManager, compute_pdf_hash


def test_compute_pdf_hash(tmp_path):
    """Test PDF hash computation."""
    # Create a test file
    test_file = tmp_path / "test.pdf"
    test_file.write_bytes(b"test pdf content")
    
    hash1 = compute_pdf_hash(test_file)
    hash2 = compute_pdf_hash(test_file)
    
    # Same file should produce same hash
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex digest length


def test_cache_manager(tmp_path):
    """Test cache manager operations."""
    cache_dir = tmp_path / "cache"
    cache_manager = CacheManager(cache_dir=cache_dir)
    
    # Verify cache directory created
    assert cache_dir.exists()
    assert (cache_dir / "cache.db").exists()


def test_cache_lookup_miss(tmp_path):
    """Test cache lookup for non-existent entry."""
    cache_dir = tmp_path / "cache"
    cache_manager = CacheManager(cache_dir=cache_dir)
    
    result = cache_manager.lookup("nonexistent_hash")
    assert result is None









def test_extraction_cache_is_keyed_on_the_parser_version(tmp_path, monkeypatch):
    """D13: a row written by an older parser must be a miss after a parser change."""
    from src import cache as cache_mod
    from src.models import CourseTerm, ExtractedCourseData
    from datetime import date

    assert isinstance(cache_mod.PARSER_VERSION, str) and len(cache_mod.PARSER_VERSION) >= 8
    cm = CacheManager(cache_dir=tmp_path / "cache")
    data = ExtractedCourseData(term=CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 8), end_date=date(2026, 12, 8)),
                               lecture_sections=[], lab_sections=[], assessments=[], course_code="TEST 1000")
    cm.store_extraction("a" * 64, data)
    assert cm.lookup_extraction("a" * 64) is not None
    monkeypatch.setattr(cache_mod, "PARSER_VERSION", "0000deadbeef")
    assert cm.lookup_extraction("a" * 64) is None, "old parser's row served after a parser change"
    cm.store_extraction("a" * 64, data)
    assert cm.lookup_extraction("a" * 64) is not None
    cm.delete_extraction("a" * 64)
    assert cm.lookup_extraction("a" * 64) is None


def test_parser_version_changes_with_the_parser_source(tmp_path):
    from src.cache import parser_version
    v1 = parser_version()
    assert v1 == parser_version()  # stable within one process
    assert v1 != parser_version(extra=b"pretend a parser file changed")


# --- FallbackCache: Postgres first, SQLite in the tmp dir when Postgres cannot be reached ---
# (2026-10-19: Neon's free compute quota ran out and every upload bounced with "could not be read")

from src.cache import FallbackCache
from src.models import AssessmentTask, CourseTerm, ExtractedCourseData, SectionOption
from datetime import date, datetime, time


class Boom(Exception):
    pass


class BrokenPrimary:
    """Stands in for a Postgres cache whose server refuses every connection."""

    def __init__(self):
        self.calls = 0

    def _fail(self, *a, **kw):
        self.calls += 1
        raise Boom("connection to server failed: Your account or project has exceeded the quota")

    ping = lookup_extraction = store_extraction = delete_extraction = _fail
    lookup_user_choices = store_user_choices = _fail


def _data():
    term = CourseTerm(term_name="Fall 2026", start_date=date(2026, 9, 8),
                      end_date=date(2026, 12, 8), timezone="America/Toronto")
    lec = SectionOption(section_type="lecture", section_id="001", days_of_week=["Mon"],
                        start_time=time(10, 30), end_time=time(11, 30), location="NCB 101")
    return ExtractedCourseData(term=term, lecture_sections=[lec], lab_sections=[], tutorial_sections=[],
                               assessments=[AssessmentTask(title="Quiz 1", type="quiz", weight_percent=10.0,
                                                           due_datetime=datetime(2026, 10, 2, 23, 59),
                                                           confidence=0.9)],
                               course_code="BIOL 1001A")


def test_fallback_cache_keeps_working_when_postgres_is_down(tmp_path):
    primary = BrokenPrimary()
    cache = FallbackCache(primary, fallback_dir=tmp_path / "fb", transient_errors=(Boom,))
    cache.store_extraction("h" * 64, _data())
    got = cache.lookup_extraction("h" * 64)
    assert got is not None and got.assessments[0].title == "Quiz 1"
    assert cache.status() == "fallback"
    assert "quota" in cache.last_error
    assert cache.ping() is False


def test_fallback_cache_does_not_hammer_a_dead_postgres(tmp_path):
    clock = {"t": 1000.0}
    primary = BrokenPrimary()
    cache = FallbackCache(primary, fallback_dir=tmp_path / "fb", transient_errors=(Boom,),
                          clock=lambda: clock["t"])
    for _ in range(5):
        cache.lookup_extraction("h" * 64)
    assert primary.calls == 1  # one failed connect, then straight to SQLite
    clock["t"] += FallbackCache.RETRY_AFTER + 1
    cache.lookup_extraction("h" * 64)
    assert primary.calls == 2  # tried Postgres again once the retry window passed


def test_fallback_cache_uses_postgres_when_it_answers(tmp_path):
    class GoodPrimary:
        def __init__(self):
            self.rows = {}

        def ping(self):
            return True

        def store_extraction(self, h, d):
            self.rows[h] = d

        def lookup_extraction(self, h):
            return self.rows.get(h)

    primary = GoodPrimary()
    cache = FallbackCache(primary, fallback_dir=tmp_path / "fb", transient_errors=(Boom,))
    cache.store_extraction("h" * 64, _data())
    assert cache.lookup_extraction("h" * 64).course_code == "BIOL 1001A"
    assert cache.status() == "ok"
    assert not (tmp_path / "fb").exists()  # SQLite never created while Postgres answers


def test_fallback_cache_lets_real_bugs_surface(tmp_path):
    class Buggy:
        def lookup_extraction(self, h):
            raise KeyError("a programming error, not a connection problem")

    cache = FallbackCache(Buggy(), fallback_dir=tmp_path / "fb", transient_errors=(Boom,))
    with pytest.raises(KeyError):
        cache.lookup_extraction("h" * 64)
