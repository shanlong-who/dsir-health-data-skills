"""Bounded WHO GHE transport, adapted from the validated GHO transport."""
from __future__ import annotations

import hashlib
import http.client
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://xmart-api-public.who.int"
TABLE = "DEX_CMS/GHE_FULL"
TABLES = {TABLE, "DEX_CMS/REF_YEAR_COD", "DEX_CMS/REF_SEX_COD", "DEX_CMS/REF_AGE_COD"}
TRANSIENT = {429, 500, 502, 503, 504}


class GHEError(Exception):
    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def as_dict(self):
        return {"status": "error", "error": {"code": self.code,
                "message": self.message, "details": self.details}}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate_url(url):
    try:
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.removeprefix("/").removesuffix("/$query")
        valid = (parsed.scheme == "https" and parsed.hostname == "xmart-api-public.who.int"
                 and parsed.port in (None, 443) and not parsed.username and not parsed.password
                 and not parsed.fragment and path in TABLES)
    except ValueError:
        valid = False
    if not valid:
        raise GHEError("unsafe_api_link", "Link is outside the approved public GHE API.", url=url)
    return url


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        before, after = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if (before.path, before.query) != (after.path, after.query):
            raise GHEError("unsafe_api_link", "Redirect changed the selected GHE resource or query.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Transport:
    def __init__(self, *, page_size=5000, max_rows=100000, max_pages=1000,
                 max_bytes=100000000, timeout=30, retries=3, transport=None, sleep=time.sleep):
        limits = (page_size, max_rows, max_pages, max_bytes, retries)
        if (any(isinstance(x, bool) or not isinstance(x, int) or x < 1 for x in limits)
                or page_size > 120000 or retries > 5
                or isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0):
            raise GHEError("invalid_query", "Invalid request or pagination limits.")
        self.page_size, self.max_rows, self.max_pages = page_size, max_rows, max_pages
        self.max_bytes, self.timeout, self.retries = max_bytes, timeout, retries
        self.transport, self.sleep = transport, sleep
        self.trace, self.total_bytes = [], 0
        self.opener = urllib.request.build_opener(CheckedRedirect())

    def url(self, path, params=None):
        if path not in TABLES:
            raise GHEError("unsafe_api_link", "Unknown GHE resource.", path=path)
        query = "&".join(f"{key}={urllib.parse.quote(str(value), safe='')}"
                         for key, value in (params or {}).items() if value is not None)
        return validate_url(BASE_URL + "/" + path + ("?" + query if query else ""))

    def request(self, path, params=None):
        original = self.url(path, params)
        parsed = urllib.parse.urlsplit(original)
        url, method, body = original, "GET", None
        if len(parsed.query.encode("utf-8")) > 1800:
            url, method = BASE_URL + "/" + path + "/$query", "POST"
            body = "&".join(f"{key}={value}" for key, value in
                            urllib.parse.parse_qsl(parsed.query)).encode("utf-8")
        for attempt in range(1, self.retries + 1):
            evidence = {"url": url, "query_url": original, "method": method,
                        "retrieved_at": utc_now(), "attempt": attempt}
            try:
                if self.transport is not None:
                    payload = self.transport(url, method=method, body=body)
                    content = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
                else:
                    headers = {"Accept": "application/json", "User-Agent": "DSIR-GHE-Skill/0.1.0"}
                    if body is not None:
                        headers["Content-Type"] = "text/plain"
                    request = urllib.request.Request(url, data=body, method=method, headers=headers)
                    with self.opener.open(request, timeout=self.timeout) as response:
                        validate_url(response.geturl())
                        content = response.read(min(self.max_bytes, 50000000) + 1)
                        content_type = response.headers.get("Content-Type", "").lower()
                    if len(content) > min(self.max_bytes, 50000000) or self.total_bytes + len(content) > self.max_bytes:
                        raise GHEError("response_limit", "GHE response exceeds the configured byte limit.")
                    if "text/html" in content_type or content.lstrip().startswith(b"<"):
                        raise GHEError("api_unavailable", "WHO returned HTML, not a GHE data response.")
                    try:
                        payload = json.loads(content.decode("utf-8-sig"),
                                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                    except (ValueError, UnicodeError) as exc:
                        raise GHEError("invalid_response", "WHO returned invalid JSON.") from exc
                self.total_bytes += len(content)
                if len(content) > min(self.max_bytes, 50000000) or self.total_bytes > self.max_bytes:
                    raise GHEError("response_limit", "GHE response exceeds the configured byte limit.")
                if not isinstance(payload, dict):
                    raise GHEError("invalid_response", "GHE OData response must be an object.")
                self.trace.append({**evidence, "status": "ok", "bytes": len(content),
                                   "sha256": hashlib.sha256(content).hexdigest()})
                return payload
            except GHEError as exc:
                self.trace.append({**evidence, "status": "error", "code": exc.code})
                if exc.code != "api_unavailable" or attempt == self.retries:
                    raise
                delay = min(2 ** attempt, 30)
            except urllib.error.HTTPError as exc:
                status = exc.code
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                exc.close()
                kind = ("invalid_request" if status in {400, 422} else
                        "temporarily_unavailable" if status in TRANSIENT else "http_error")
                self.trace.append({**evidence, "status": "error",
                                   "http_status": status, "failure_kind": kind})
                if status not in TRANSIENT or attempt == self.retries:
                    raise GHEError("who_api_request_failed", "WHO request failed; no empty result established.",
                                   http_status=status, failure_kind=kind, url=original) from exc
                delay = min(float(retry_after), 30) if retry_after.isdigit() else min(2 ** attempt, 30)
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError,
                    http.client.HTTPException, OSError) as exc:
                self.trace.append({**evidence, "status": "error", "failure_kind": "network_error"})
                if attempt == self.retries:
                    raise GHEError("who_api_request_failed", "Cannot reach WHO; check host network access.",
                                   failure_kind="network_error", reason=str(exc), url=original) from exc
                delay = min(2 ** attempt, 30)
            self.sleep(delay)
        raise AssertionError("unreachable")

    @staticmethod
    def records(payload):
        rows = payload.get("value")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise GHEError("invalid_response", "Malformed WHO OData records.")
        return rows

    def reference(self, path, top):
        payload = self.request(path, {"$top": top})
        rows = self.records(payload)
        if len(rows) >= top or payload.get("@odata.nextLink"):
            raise GHEError("incomplete_data", "Reference catalogue was truncated.")
        if not rows or any(not {"CODE", "TITLE"}.issubset(row) for row in rows):
            raise GHEError("invalid_catalogue", "Reference catalogue is empty or malformed.")
        codes = [str(row["CODE"]) for row in rows]
        if (any(isinstance(row["CODE"], bool) or not isinstance(row["CODE"], (str, int))
                or not str(row["CODE"]).strip() for row in rows) or len(set(codes)) != len(codes)):
            raise GHEError("invalid_catalogue", "Reference catalogue has missing or duplicate codes.")
        return rows

    def collection(self, filter_text, fields):
        params = {"$filter": filter_text, "$select": ",".join(dict.fromkeys(["Sys_PK", *fields])),
                  "$orderby": "Sys_PK", "$count": "true", "$top": self.page_size, "$skip": 0}
        start, rows, identifiers, schema, total = len(self.trace), [], set(), None, None
        for page in range(self.max_pages):
            payload = self.request(TABLE, params)
            chunk = self.records(payload)
            count = payload.get("@odata.count")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise GHEError("incomplete_data", "WHO did not supply a valid total row count.")
            if total is None:
                total = count
            if count != total:
                raise GHEError("incomplete_data", "WHO row count changed between pages.")
            if total > self.max_rows:
                raise GHEError("response_limit", "Narrow the query; too many source rows.", total=total)
            if len(chunk) > self.page_size or len(rows) + len(chunk) > total or (not chunk and len(rows) < total):
                raise GHEError("incomplete_data", "Unexpected or missing WHO data page.")
            if payload.get("@odata.nextLink"):
                next_url = urllib.parse.urljoin(BASE_URL + "/" + TABLE, payload["@odata.nextLink"])
                validate_url(next_url)
                if urllib.parse.urlsplit(next_url).path != "/" + TABLE:
                    raise GHEError("unsafe_api_link", "Pagination link changed the GHE table.")
            for row in chunk:
                current = set(row)
                if schema is None:
                    schema = current
                if schema != current or not set(fields).issubset(current):
                    raise GHEError("invalid_response", "WHO observation schema changed or lost selected fields.")
                identifier = row.get("Sys_PK")
                if (isinstance(identifier, bool) or not isinstance(identifier, (str, int))
                        or not str(identifier).strip() or str(identifier) in identifiers):
                    raise GHEError("incomplete_data", "Missing or repeated WHO observation identifier.")
                identifiers.add(str(identifier))
            rows.extend(chunk)
            if len(rows) == total:
                if payload.get("@odata.nextLink"):
                    raise GHEError("incomplete_data", "WHO next link contradicts the declared complete count.")
                return {"records": rows, "provenance": {
                    "source": "WHO Global Health Estimates", "backend": "xmart", "base_url": BASE_URL,
                    "table": TABLE, "filter": filter_text, "selected_fields": fields,
                    "complete": True, "source_rows": total, "pages": page + 1,
                    "retrieved_at": utc_now(), "requests": self.trace[start:]}}
            params["$skip"] = len(rows)
        raise GHEError("incomplete_data", "GHE pagination limit reached before completion.")
