import httpx
import pytest

from aurora.collector.static_url import StaticUrlCollector
from aurora.ingestion.errors import (
    WebPrivateAddressBlockedError,
    WebResponseTooLargeError,
    WebUnsupportedContentTypeError,
)


def _public_resolver(host: str, port: int) -> list[str]:
    return ["93.184.216.34"]


def test_static_url_collector_fetches_html_and_records_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html; charset=utf-8",
                "etag": '"abc"',
            },
            content="<html><body><article><p>Hello</p></article></body></html>".encode(),
        )

    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(handler),
    )
    result = collector.collect("https://example.com/article", max_bytes=4096)
    assert result.input_uri == "https://example.com/article"
    assert result.media_type == "text/html"
    assert "Hello" in result.text
    assert result.response_metadata["etag"] == '"abc"'


def test_static_url_collector_blocks_private_targets():
    collector = StaticUrlCollector(resolver=lambda host, port: ["127.0.0.1"])
    with pytest.raises(WebPrivateAddressBlockedError):
        collector.collect("http://example.test/article", max_bytes=1024)


def test_redirect_target_is_revalidated_for_private_network():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "public.test":
            return httpx.Response(302, headers={"location": "http://private.test/x"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>x</p>")

    def resolver(host: str, port: int) -> list[str]:
        return ["93.184.216.34"] if host == "public.test" else ["10.0.0.5"]

    collector = StaticUrlCollector(
        resolver=resolver,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(WebPrivateAddressBlockedError):
        collector.collect("http://public.test/start", max_bytes=1024)


def test_static_url_size_limit_is_enforced_during_stream():
    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"x" * 100,
            )
        ),
    )
    with pytest.raises(WebResponseTooLargeError):
        collector.collect("https://example.com/large", max_bytes=10)


def test_static_url_rejects_non_html_content_type():
    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "application/pdf"},
                content=b"%PDF",
            )
        ),
    )
    with pytest.raises(WebUnsupportedContentTypeError):
        collector.collect("https://example.com/file", max_bytes=1024)


def test_default_resolver_deduplicates_addresses(monkeypatch):
    from aurora.collector import static_url

    monkeypatch.setattr(
        static_url.socket,
        "getaddrinfo",
        lambda host, port, type: [
            (2, 1, 6, "", ("93.184.216.34", port)),
            (2, 1, 6, "", ("93.184.216.34", port)),
            (10, 1, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", port, 0, 0)),
        ],
    )
    assert static_url._default_resolver("example.com", 443) == [
        "93.184.216.34",
        "2606:2800:220:1:248:1893:25c8:1946",
    ]


def test_redirect_without_location_is_an_http_error():
    from aurora.ingestion.errors import WebHttpError

    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(lambda request: httpx.Response(302)),
    )
    with pytest.raises(WebHttpError):
        collector.collect("https://example.com/start", max_bytes=1024)


def test_redirect_limit_is_enforced():
    from aurora.ingestion.errors import WebTooManyRedirectsError

    collector = StaticUrlCollector(
        max_redirects=0,
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": "/again"})
        ),
    )
    with pytest.raises(WebTooManyRedirectsError):
        collector.collect("https://example.com/start", max_bytes=1024)


def test_http_status_error_is_wrapped():
    from aurora.ingestion.errors import WebHttpError

    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(503, headers={"content-type": "text/html"})
        ),
    )
    with pytest.raises(WebHttpError):
        collector.collect("https://example.com/down", max_bytes=1024)


def test_invalid_encoding_is_reported():
    from aurora.ingestion.errors import InvalidEncodingError

    collector = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html; charset=utf-8"},
                content=b"\xff\xfe",
            )
        ),
    )
    with pytest.raises(InvalidEncodingError):
        collector.collect("https://example.com/bad", max_bytes=1024)


def test_invalid_and_credential_urls_are_rejected():
    from aurora.ingestion.errors import WebInvalidUrlError

    collector = StaticUrlCollector(resolver=_public_resolver)
    with pytest.raises(WebInvalidUrlError):
        collector.collect("ftp://example.com/file", max_bytes=1024)
    with pytest.raises(WebInvalidUrlError):
        collector.collect("https://user:secret@example.com/file", max_bytes=1024)


def test_dns_failures_and_empty_resolution_are_reported():
    from aurora.ingestion.errors import WebHttpError

    failing = StaticUrlCollector(
        resolver=lambda host, port: (_ for _ in ()).throw(OSError("dns"))
    )
    with pytest.raises(WebHttpError):
        failing.collect("https://example.com/a", max_bytes=1024)

    empty = StaticUrlCollector(resolver=lambda host, port: [])
    with pytest.raises(WebHttpError):
        empty.collect("https://example.com/a", max_bytes=1024)


def test_timeout_and_transport_errors_are_wrapped():
    from aurora.ingestion.errors import WebFetchTimeoutError, WebHttpError

    timeout = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ReadTimeout("slow", request=request))
        ),
    )
    with pytest.raises(WebFetchTimeoutError):
        timeout.collect("https://example.com/slow", max_bytes=1024)

    broken = StaticUrlCollector(
        resolver=_public_resolver,
        transport=httpx.MockTransport(
            lambda request: (_ for _ in ()).throw(httpx.ConnectError("down", request=request))
        ),
    )
    with pytest.raises(WebHttpError):
        broken.collect("https://example.com/down", max_bytes=1024)
