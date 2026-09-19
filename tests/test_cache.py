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
