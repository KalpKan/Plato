"""Configuration guard-rails for running on Vercel (fail fast, /tmp only)."""
import importlib
import sys

import pytest


def _reload_app(monkeypatch, **env):
    for k in ("SECRET_KEY", "DATABASE_URL", "PLATO_TMP_DIR"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def test_missing_secret_key_fails_fast(monkeypatch):
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _reload_app(monkeypatch)


def test_upload_dir_under_tmp(monkeypatch, tmp_path):
    mod = _reload_app(monkeypatch, SECRET_KEY="x", PLATO_TMP_DIR=str(tmp_path))
    d = mod.upload_dir()
    assert d.exists()
    assert str(d).startswith(str(tmp_path))


def test_max_upload_is_16mb(monkeypatch, tmp_path):
    mod = _reload_app(monkeypatch, SECRET_KEY="x", PLATO_TMP_DIR=str(tmp_path))
    assert mod.app.config["MAX_CONTENT_LENGTH"] == 16 * 1024 * 1024


def test_cache_is_lazy(monkeypatch, tmp_path):
    """Importing the app must not open a database connection (cold-start cost)."""
    mod = _reload_app(monkeypatch, SECRET_KEY="x", PLATO_TMP_DIR=str(tmp_path),
                      DATABASE_URL="postgresql://nobody:nothing@127.0.0.1:1/none")
    assert mod._cache is None
