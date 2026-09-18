"""PostHog wiring: /ingest reverse proxy, browser snippet, server-side events."""
import importlib
import io
import sys

from src import analytics


def _app(monkeypatch, tmp_path, key=""):
    monkeypatch.setenv("SECRET_KEY", "test")
    monkeypatch.setenv("PLATO_TMP_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if key:
        monkeypatch.setenv("POSTHOG_API_KEY", key)
    else:
        monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    sys.modules.pop("src.app", None)
    return importlib.import_module("src.app")


def test_capture_is_noop_without_key(monkeypatch):
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    assert analytics.capture("sid", "pdf_uploaded", {"x": 1}) is False


def test_snippet_present_only_with_key(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path)
    assert b"posthog.init" not in mod.app.test_client().get("/").data
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    html = mod.app.test_client().get("/").data
    assert b"posthog.init('phc_test123'" in html
    assert b"api_host: '/ingest'" in html
    assert b"persistence: 'memory'" in html
    assert b"autocapture: true" in html


def test_ingest_proxy_forwards_to_posthog(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    seen = {}

    class FakeResp(io.BytesIO):
        status = 200
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["method"] = req.get_method()
        seen["body"] = req.data
        return FakeResp(b'{"status":1}')

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    r = mod.app.test_client().post("/ingest/e/?ip=1", data=b'{"a":1}', content_type="application/json")
    assert r.status_code == 200
    assert r.data == b'{"status":1}'
    assert seen["url"] == "https://us.i.posthog.com/e/?ip=1"
    assert seen["method"] == "POST" and seen["body"] == b'{"a":1}'


def test_ingest_static_assets_go_to_assets_host(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    seen = {}

    class FakeResp(io.BytesIO):
        status = 200
        headers = {"Content-Type": "application/javascript"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        return FakeResp(b"//js")

    monkeypatch.setattr(mod.urllib.request, "urlopen", fake_urlopen)
    r = mod.app.test_client().get("/ingest/static/array.js")
    assert r.status_code == 200
    assert seen["url"] == "https://us-assets.i.posthog.com/static/array.js"


def test_upload_emits_pdf_uploaded_and_pdf_parsed(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    events = []
    monkeypatch.setattr(mod.analytics, "capture", lambda d, e, p=None: events.append(e) or True)

    class FakeExtractor:
        def __init__(self, path):
            pass

        def extract_all(self):
            from tests.test_flow import _data
            return _data()

    monkeypatch.setattr(mod, "PDFExtractor", FakeExtractor)
    r = mod.app.test_client().post("/upload", data={"pdf_file": (io.BytesIO(b"%PDF-1.4 fake"), "outline.pdf")},
                                   content_type="multipart/form-data")
    assert r.status_code == 302 and r.headers["Location"].endswith("/review")
    assert events == ["pdf_uploaded", "pdf_parsed"]


def _fake_urlopen(seen, resp_headers=None, body=b'{"status":1}'):
    class FakeResp(io.BytesIO):
        status = 200
        headers = resp_headers or {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        seen["url"] = req.full_url
        seen["headers"] = dict(req.headers)
        return FakeResp(body)

    return fake_urlopen


def test_ingest_proxy_never_forwards_cookie_or_authorization(monkeypatch, tmp_path):
    """The signed Flask session cookie is a bearer for the visitor's review session;
    it must never leave the app. Only a short whitelist of headers is forwarded."""
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    seen = {}
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(seen))
    c = mod.app.test_client()
    with c.session_transaction() as s:
        s["pdf_hash"] = "h" * 64
    r = c.post("/ingest/e/", data=b'{"a":1}', content_type="application/json",
               headers={"Authorization": "Bearer secret", "X-Custom": "1",
                        "User-Agent": "UA/1", "Origin": "https://plato.kalpkan.com",
                        "Referer": "https://plato.kalpkan.com/", "Accept": "*/*"})
    assert r.status_code == 200
    sent = {k.lower() for k in seen["headers"]}
    assert "cookie" not in sent
    assert "authorization" not in sent
    assert "x-custom" not in sent
    assert sent <= {"content-type", "user-agent", "accept", "origin", "referer", "x-forwarded-for"}
    assert seen["headers"].get("User-agent") == "UA/1"
    assert seen["headers"].get("Content-type") == "application/json"


def test_ingest_static_forwards_cache_headers(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    seen = {}
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(
        seen, {"Content-Type": "application/javascript", "Cache-Control": "public, max-age=3600",
               "ETag": '"abc"', "Last-Modified": "Wed, 01 Jan 2025 00:00:00 GMT"}, b"//js"))
    r = mod.app.test_client().get("/ingest/static/array.js")
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "public, max-age=3600"
    assert r.headers["ETag"] == '"abc"'
    assert r.headers["Last-Modified"] == "Wed, 01 Jan 2025 00:00:00 GMT"


def test_ingest_event_endpoint_does_not_forward_cache_headers(monkeypatch, tmp_path):
    mod = _app(monkeypatch, tmp_path, key="phc_test123")
    seen = {}
    monkeypatch.setattr(mod.urllib.request, "urlopen", _fake_urlopen(
        seen, {"Content-Type": "application/json", "ETag": '"abc"'}))
    r = mod.app.test_client().post("/ingest/e/", data=b"{}", content_type="application/json")
    assert r.status_code == 200
    assert "ETag" not in r.headers
