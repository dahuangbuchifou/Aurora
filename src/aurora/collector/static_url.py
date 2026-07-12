"""Safe single-URL static HTTP(S) collector."""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urljoin, urlsplit

import httpx

from aurora.ingestion.errors import (
    InvalidEncodingError,
    WebFetchTimeoutError,
    WebHttpError,
    WebInvalidUrlError,
    WebPrivateAddressBlockedError,
    WebResponseTooLargeError,
    WebTooManyRedirectsError,
    WebUnsupportedContentTypeError,
)
from aurora.ingestion.hashing import normalize_text
from aurora.ingestion.identity import normalize_http_url

from .base import CollectedInput, Collector

Resolver = Callable[[str, int], list[str]]


def _default_resolver(host: str, port: int) -> list[str]:
    addresses: list[str] = []
    for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM):
        address = item[4][0]
        if address not in addresses:
            addresses.append(address)
    return addresses


def _is_blocked_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
    )


class StaticUrlCollector(Collector):
    """Fetch one explicit static HTML URL with SSRF and resource controls."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 15.0,
        max_redirects: int = 5,
        allow_private_network: bool = False,
        resolver: Resolver | None = None,
        transport: httpx.BaseTransport | None = None,
        user_agent: str = "Aurora/0.5.0",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.allow_private_network = allow_private_network
        self.resolver = resolver or _default_resolver
        self.transport = transport
        self.user_agent = user_agent

    def collect(self, url: str, *, max_bytes: int) -> CollectedInput:
        current = self._validate_url(url)
        redirect_chain: list[str] = []
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                },
            ) as client:
                for redirect_no in range(self.max_redirects + 1):
                    self._validate_network_target(current)
                    with client.stream("GET", current) as response:
                        if response.status_code in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                raise WebHttpError(
                                    "redirect response has no Location header",
                                    context={
                                        "url": current,
                                        "status_code": response.status_code,
                                    },
                                )
                            if redirect_no >= self.max_redirects:
                                raise WebTooManyRedirectsError(
                                    "URL exceeded redirect limit",
                                    context={
                                        "url": current,
                                        "max_redirects": self.max_redirects,
                                    },
                                )
                            redirect_chain.append(current)
                            current = self._validate_url(urljoin(current, location))
                            continue

                        if response.status_code >= 400:
                            raise WebHttpError(
                                "HTTP request failed",
                                context={
                                    "url": current,
                                    "status_code": response.status_code,
                                },
                            )
                        media_type = (
                            response.headers.get("content-type", "")
                            .split(";", 1)[0]
                            .strip()
                            .lower()
                        )
                        if media_type not in {"text/html", "application/xhtml+xml"}:
                            raise WebUnsupportedContentTypeError(
                                "URL did not return static HTML",
                                context={
                                    "url": current,
                                    "content_type": media_type or None,
                                },
                            )
                        declared_length = response.headers.get("content-length")
                        if declared_length and int(declared_length) > max_bytes:
                            raise WebResponseTooLargeError(
                                "HTML response exceeds size limit",
                                context={
                                    "url": current,
                                    "max_bytes": max_bytes,
                                    "content_length": int(declared_length),
                                },
                            )
                        chunks: list[bytes] = []
                        total = 0
                        for chunk in response.iter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                raise WebResponseTooLargeError(
                                    "HTML response exceeds size limit",
                                    context={
                                        "url": current,
                                        "max_bytes": max_bytes,
                                        "received_bytes": total,
                                    },
                                )
                            chunks.append(chunk)
                        raw = b"".join(chunks)
                        charset = response.encoding or "utf-8"
                        try:
                            text = raw.decode(charset)
                        except (UnicodeDecodeError, LookupError) as exc:
                            raise InvalidEncodingError(
                                "HTML response encoding could not be decoded",
                                context={"url": current, "encoding": charset},
                            ) from exc
                        return CollectedInput(
                            path=None,
                            input_uri=normalize_http_url(current),
                            file_name=(
                                urlsplit(current).path.rsplit("/", 1)[-1]
                                or "index.html"
                            ),
                            suffix=".html",
                            size_bytes=len(raw),
                            text=normalize_text(text),
                            raw_bytes=raw,
                            media_type=media_type,
                            response_metadata={
                                "status_code": response.status_code,
                                "final_url": normalize_http_url(current),
                                "redirect_chain": redirect_chain,
                                "content_type": response.headers.get("content-type"),
                                "etag": response.headers.get("etag"),
                                "last_modified": response.headers.get("last-modified"),
                            },
                        )
        except httpx.TimeoutException as exc:
            raise WebFetchTimeoutError(
                "URL fetch timed out",
                context={
                    "url": current,
                    "timeout_seconds": self.timeout_seconds,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise WebHttpError(
                "URL fetch failed",
                context={
                    "url": current,
                    "exception_type": type(exc).__name__,
                },
            ) from exc

    @staticmethod
    def _validate_url(url: str) -> str:
        raw = urlsplit(str(url).strip())
        if raw.username or raw.password:
            raise WebInvalidUrlError(
                "credentials in URL are not supported",
                context={"url": str(url)},
            )
        try:
            return normalize_http_url(url)
        except (ValueError, TypeError) as exc:
            raise WebInvalidUrlError(
                "URL must be an absolute HTTP(S) address",
                context={"url": str(url)},
            ) from exc

    def _validate_network_target(self, url: str) -> None:
        if self.allow_private_network:
            return
        parsed = urlsplit(url)
        host = parsed.hostname
        if not host:
            raise WebInvalidUrlError("URL has no hostname", context={"url": url})
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            addresses = self.resolver(host, port)
        except OSError as exc:
            raise WebHttpError(
                "DNS resolution failed",
                context={"url": url, "host": host},
            ) from exc
        if not addresses:
            raise WebHttpError(
                "DNS resolution returned no addresses",
                context={"url": url, "host": host},
            )
        blocked = [address for address in addresses if _is_blocked_address(address)]
        if blocked:
            raise WebPrivateAddressBlockedError(
                "private or non-routable URL target is blocked",
                context={"url": url, "blocked_addresses": blocked},
            )
