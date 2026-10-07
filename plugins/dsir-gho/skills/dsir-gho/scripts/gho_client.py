"""WHO GHO transport; xMart by default, explicit legacy compatibility only."""
from __future__ import annotations

import hashlib
import http.client
import json
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://xmart-api-public.who.int"
LEGACY_BASE_URL = "https://ghoapi.azureedge.net/api"
TRANSIENT = {429, 500, 502, 503, 504}


class GHOError(Exception):
    """A failed query is never represented as an empty successful table."""

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details

    def as_dict(self):
        return {"status": "error", "error": {"code": self.code,
                "message": self.message, "details": self.details}}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def validate_code(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", value):
        raise GHOError("invalid_query", "Indicator/dimension code must be a nonempty catalogue code.")
    return value


def validate_url(url, backend="xmart"):
    try:
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise GHOError("unsafe_api_link", "WHO returned a malformed API URL.", url=url) from exc
    approved_host = "xmart-api-public.who.int" if backend == "xmart" else "ghoapi.azureedge.net"
    approved_path = (re.fullmatch(r"/DATA_/[A-Za-z0-9_]+(?:/\$query)?", parsed.path)
                     if backend == "xmart" else parsed.path.startswith("/api/"))
    if (parsed.scheme != "https" or parsed.hostname != approved_host
            or port not in (None, 443) or parsed.username or parsed.password
            or not approved_path or parsed.fragment):
        raise GHOError("unsafe_api_link", "WHO returned a link outside the approved GHO API.", url=url)
    return url


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, backend):
        self.backend = backend

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        try:
            validate_url(newurl, self.backend)
            if urllib.parse.urlsplit(req.full_url).path != urllib.parse.urlsplit(newurl).path:
                raise GHOError("unsafe_api_link", "WHO redirect changed the requested API resource.", url=newurl)
        except GHOError as exc:
            exc.details.update(request_url=req.full_url, http_status=code, backend=self.backend)
            raise
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GHOClient:
    def __init__(self, *, backend="xmart", timeout=30, retries=3, page_size=5000,
                 max_pages=10000, max_rows=1000000, max_bytes=500000000,
                 transport=None, sleep=time.sleep):
        if not all(isinstance(x, int) and not isinstance(x, bool) and x > 0
                   for x in (retries, page_size, max_pages, max_rows, max_bytes)) or timeout <= 0:
            raise GHOError("invalid_query", "Client limits must be positive.")
        if backend not in {"xmart", "legacy"}:
            raise GHOError("invalid_query", "backend must be xmart or legacy.")
        if backend == "xmart" and page_size > 120000:
            raise GHOError("invalid_query", "xMart page_size must not exceed 120000.")
        self.backend = backend
        self.base_url = BASE_URL if backend == "xmart" else LEGACY_BASE_URL
        self.timeout, self.retries, self.page_size = timeout, retries, page_size
        self.max_pages, self.max_rows, self.max_bytes = max_pages, max_rows, max_bytes
        self.transport, self.sleep = transport, sleep
        self.trace = []
        self._catalogue = None
        self._dimensions = {}
        self._opener = urllib.request.build_opener(_CheckedRedirect(backend))
        from xmart import XMartAdapter
        self._xmart = XMartAdapter(self) if backend == "xmart" else None

    def url(self, path, params=None):
        url = self.base_url + "/" + path.lstrip("/")
        if params:
            if self.backend == "xmart":
                # Match DSIR: encode values and retain literal OData names.
                url += "?" + "&".join(f"{key}={urllib.parse.quote(str(value), safe='')}" for key, value in params.items())
            else:
                url += "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        return validate_url(url, self.backend)

    def _request(self, url):
        validate_url(url, self.backend)
        request_url, method, request_body = url, "GET", None
        parsed = urllib.parse.urlsplit(url)
        if self.backend == "xmart" and len(parsed.query.encode("utf-8")) > 1800:
            request_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path + "/$query", "", ""))
            method = "POST"
            request_body = "&".join(f"{key}={value}" for key, value in urllib.parse.parse_qsl(parsed.query)).encode("utf-8")
            validate_url(request_url, self.backend)
        for attempt in range(1, self.retries + 1):
            try:
                if self.transport:
                    payload = (self.transport(request_url, method=method, body=request_body)
                               if request_body is not None else self.transport(request_url))
                    content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                else:
                    headers = {"Accept": "application/json", "User-Agent": "DSIR-GHO-Skill/0.1.1"}
                    if request_body is not None:
                        headers["Content-Type"] = "text/plain"
                    request = urllib.request.Request(request_url, data=request_body, method=method, headers=headers)
                    with self._opener.open(request, timeout=self.timeout) as response:
                        validate_url(response.geturl(), self.backend)
                        content = response.read(min(self.max_bytes, 50000000) + 1)
                    if len(content) > min(self.max_bytes, 50000000):
                        raise GHOError("response_limit", "API page exceeds the configured byte limit.", url=url)
                    try:
                        payload = json.loads(content.decode("utf-8-sig"))
                    except (ValueError, UnicodeError) as exc:
                        raise GHOError("invalid_response", "WHO API returned invalid JSON, not a data result.", url=url) from exc
                self.trace.append({"url": request_url, "query_url": url, "method": method,
                                   "query_body_sha256": hashlib.sha256(request_body).hexdigest() if request_body else None,
                                   "backend": self.backend, "retrieved_at": utc_now(), "attempt": attempt,
                                   "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
                return payload, len(content)
            except GHOError as exc:
                self.trace.append({"url": request_url, "query_url": url, "method": method,
                                   "backend": self.backend, "retrieved_at": utc_now(), "attempt": attempt,
                                   "status": "error", "error": exc.as_dict()["error"]})
                raise
            except urllib.error.HTTPError as exc:
                if exc.code not in TRANSIENT or attempt == self.retries:
                    raise GHOError("who_api_request_failed", "WHO API request failed.",
                                   url=url, http_status=exc.code, attempts=attempt) from exc
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                delay = min(float(retry_after), 30) if retry_after.isdigit() else min(2 ** attempt, 30)
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError,
                    http.client.HTTPException, OSError) as exc:
                if attempt == self.retries:
                    raise GHOError("who_api_request_failed", "WHO API could not be reached; check network permissions and connectivity.",
                                   url=url, attempts=attempt, reason=str(exc)) from exc
                delay = min(2 ** attempt, 30)
            self.sleep(delay)
        raise AssertionError("unreachable")

    def collection(self, path, params=None, *, paged=False, page_size=None, group=None):
        """Follow nextLink; managed $skip paging requires a stable total count."""
        params = dict(params or {})
        if self.backend == "xmart" and params.get("$orderby") == "Sys_PK" and params.get("$select"):
            params["$select"] = ",".join(dict.fromkeys(["Sys_PK", *params["$select"].split(",")]))
        effective_size = page_size or self.page_size
        if self.backend == "xmart" and not 1 <= effective_size <= 120000:
            raise GHOError("invalid_query", "xMart page_size must be from 1 to 120000.")
        if group:
            if self.backend != "xmart" or len(group) > 6 or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", f) for f in group):
                raise GHOError("invalid_query", "xMart distinct queries require one to six verified fields.")
            apply = "groupby((" + ",".join(group) + "))"
            if params.get("$filter"):
                apply = "filter(" + params.pop("$filter") + ")/" + apply
            params.update({"$apply": apply, "$orderby": ",".join(group)})
            params.pop("$count", None)
            paged = True
        if paged:
            params.update({"$top": effective_size, "$skip": 0})
            if not group:
                params["$count"] = "true"
        first_url = self.url(path, params)
        url, seen, rows, pages, size, declared = first_url, set(), [], 0, 0, None
        visited, previous, schema, identifiers, field_types = [], None, None, set(), {}
        while url:
            if url in seen:
                raise GHOError("incomplete_data", "Pagination cycle detected; no complete result is available.", url=url)
            if pages >= self.max_pages:
                raise GHOError("incomplete_data", "Page limit reached; narrow the query or increase the limit.")
            seen.add(url)
            visited.append(url)
            body, byte_count = self._request(url)
            size += byte_count
            if size > self.max_bytes:
                raise GHOError("incomplete_data", "Total response byte limit reached.")
            if not isinstance(body, dict) or not isinstance(body.get("value"), list):
                raise GHOError("invalid_response", "WHO response is missing an OData value array.", url=url)
            page = body["value"]
            if any(not isinstance(item, dict) for item in page):
                raise GHOError("invalid_response", "WHO value array contains non-record values.", url=url)
            count = None if group else body.get("@odata.count")
            if count is not None:
                valid_count = (isinstance(count, (int, float)) and not isinstance(count, bool)
                               and math.isfinite(count) and count >= 0 and count == int(count))
                if not valid_count:
                    raise GHOError("invalid_response", "WHO returned an invalid row count.", url=url)
                if declared is not None and declared != count:
                    raise GHOError("incomplete_data", "WHO row count changed during pagination; retry the query.")
                declared = count
            if paged and not group and declared is None:
                raise GHOError("incomplete_data", "WHO omitted the count required to verify managed pagination.")
            if self.backend == "xmart" and paged:
                if declared is not None and declared > self.max_rows:
                    raise GHOError("incomplete_data", "WHO declared more rows than the configured row limit.")
                if len(page) > effective_size or (page and page == previous):
                    raise GHOError("incomplete_data", "Oversized or repeated xMart page.")
                for item in page:
                    fields = tuple(item)
                    if schema is None:
                        schema = fields
                    elif fields != schema:
                        raise GHOError("incomplete_data", "xMart page schema changed during retrieval.")
                    for field, value in item.items():
                        if value is not None:
                            kind = "number" if isinstance(value, (int, float)) and not isinstance(value, bool) else type(value).__name__
                            if field in field_types and field_types[field] != kind:
                                raise GHOError("incomplete_data", "xMart field types changed during retrieval.", field=field)
                            field_types[field] = kind
                    if params.get("$orderby") == "Sys_PK":
                        identifier = item.get("Sys_PK")
                        if (not isinstance(identifier, (str, int, float)) or isinstance(identifier, bool)
                                or isinstance(identifier, float) and not math.isfinite(identifier)
                                or identifier in identifiers):
                            raise GHOError("incomplete_data", "Missing or duplicate xMart Sys_PK identifier.")
                        identifiers.add(identifier)
                previous = page
            rows.extend(page)
            pages += 1
            if len(rows) > self.max_rows:
                raise GHOError("incomplete_data", "Row limit reached; narrow the query or increase the limit.")
            next_link = body.get("@odata.nextLink")
            if next_link:
                if not isinstance(next_link, str):
                    raise GHOError("invalid_response", "WHO returned an invalid nextLink.")
                url = validate_url(urllib.parse.urljoin(url, next_link), self.backend)
                if urllib.parse.urlsplit(url).path != urllib.parse.urlsplit(first_url).path:
                    raise GHOError("unsafe_api_link", "Pagination switched to another API resource.", url=url)
            elif group and len(page) == effective_size:
                params["$skip"] = len(rows)
                url = self.url(path, params)
            elif paged and not group and len(rows) < declared:
                if not page:
                    raise GHOError("incomplete_data", "Pagination ended before the declared total.")
                params["$skip"] = len(rows)
                url = self.url(path, params)
            else:
                url = None
        # A limited probe intentionally asks for less than the total.
        if declared is not None and (paged or "$top" not in params) and len(rows) != declared:
            raise GHOError("incomplete_data", "Retrieved rows do not match WHO's total count.", expected=declared, actual=len(rows))
        return {"records": rows, "provenance": {"query_url": first_url, "urls": visited,
                "pages": pages, "row_count": len(rows), "declared_count": declared,
                "complete": paged or "$top" not in params,
                "pagination": "short-page-verified groupby/skip" if group else "count-verified nextLink/skip" if paged else "nextLink",
                "retrieved_at": utc_now(), "source": "WHO GHO", "backend": self.backend,
                "base_url": self.base_url, "table": path, "filter": params.get("$filter"),
                "group_fields": group}}

    def catalogue(self):
        if self._xmart:
            return self._xmart.catalogue()
        if self._catalogue is None:
            data = self.collection("Indicator", {"$orderby": "IndicatorCode"}, paged=True, page_size=1000)
            rows = data["records"]
            if not rows or any(not isinstance(row.get("IndicatorCode"), str)
                               or not isinstance(row.get("IndicatorName"), str) for row in rows):
                raise GHOError("invalid_catalogue", "WHO indicator catalogue is empty or malformed.")
            self._catalogue = rows
        return self._catalogue

    def confirm_indicator(self, code):
        validate_code(code)
        matches = [row for row in self.catalogue() if row["IndicatorCode"].casefold() == code.casefold()]
        if not matches:
            raise GHOError("indicator_not_found", "Indicator is not present in the successfully retrieved WHO catalogue.", indicator=code)
        return matches[0]

    def dimension_values(self, dimension):
        if self._xmart:
            return self._xmart.dimension_values(dimension)
        validate_code(dimension)
        if dimension not in self._dimensions:
            self._dimensions[dimension] = self.collection(
                f"DIMENSION/{dimension}/DimensionValues", {"$orderby": "Code"}, paged=True, page_size=1000)["records"]
        return self._dimensions[dimension]

    def indicator_dimensions(self, code):
        if self._xmart:
            return self._xmart.indicator_dimensions(code)
        code = self.confirm_indicator(code)["IndicatorCode"]
        return self.collection(f"Indicator({literal(code)})/Dimensions")["records"]

    def get_gho_data(self, indicator, locations=None, year_from=None, year_to=None,
                     dimensions=None, spatial_type=None):
        if self._xmart:
            return self._xmart.get_data(indicator, locations, year_from, year_to, dimensions, spatial_type)
        entry = self.confirm_indicator(indicator)
        code = entry["IndicatorCode"]
        filters, selected = [], {}
        if spatial_type is not None:
            spatial_type = str(spatial_type).upper()
            if spatial_type not in {"COUNTRY", "REGION", "GLOBAL"}:
                raise GHOError("invalid_query", "spatial_type must be COUNTRY, REGION or GLOBAL.")
        if locations is not None:
            if not isinstance(locations, (str, list, tuple)):
                raise GHOError("invalid_query", "locations must be a string or list of location codes.")
            locations = [locations] if isinstance(locations, str) else list(locations)
            if not locations or any(not isinstance(x, str) or not x.strip() for x in locations):
                raise GHOError("invalid_query", "locations must contain nonempty resolved WHO codes.")
            from locations import resolve_locations
            resolved = resolve_locations(locations, client=self)
            if resolved["status"] != "ok":
                raise GHOError(resolved["status"], "Location resolution requires clarification.", resolution=resolved)
            locations = [item["code"] for item in resolved["locations"]]
            types = {item["spatial_type"].upper() for item in resolved["locations"]}
            if len(types) != 1:
                raise GHOError("invalid_query", "Query countries and regional aggregates separately.")
            resolved_type = types.pop()
            if spatial_type is not None and spatial_type != resolved_type:
                raise GHOError("invalid_query", "Resolved locations do not match the supplied spatial_type.")
            spatial_type = resolved_type
            filters.append("SpatialDim in (" + ",".join(map(literal, locations)) + ")")
        if spatial_type is not None:
            filters.insert(0, "SpatialDimType eq " + literal(spatial_type))
        for name, year, comparison in (("year_from", year_from, "ge"), ("year_to", year_to, "le")):
            if year is not None:
                if not isinstance(year, int) or isinstance(year, bool) or not 1 <= year <= 9999:
                    raise GHOError("invalid_query", f"{name} must be an integer year from 1 to 9999.")
                filters.append(f"TimeDim {comparison} {year}")
        if year_from is not None and year_to is not None and year_from > year_to:
            raise GHOError("invalid_query", "year_from must not exceed year_to.")
        if dimensions is not None and not isinstance(dimensions, dict):
            raise GHOError("invalid_query", "dimensions must map dim1, dim2 or dim3 to code lists.")
        for dimension, values in (dimensions or {}).items():
            key = str(dimension).lower()
            if key not in {"dim1", "dim2", "dim3"}:
                raise GHOError("invalid_query", "Only dim1, dim2 and dim3 filters are supported.")
            if not isinstance(values, (str, list, tuple)):
                raise GHOError("invalid_query", "Dimension filters require strings or lists of codes.")
            values = [values] if isinstance(values, str) else list(values)
            if not values or any(not isinstance(v, str) or not v for v in values):
                raise GHOError("invalid_query", "Dimension filters require nonempty code lists.")
            selected[key] = values
            filters.append(key.capitalize() + " in (" + ",".join(map(literal, values)) + ")")
        params = {"$orderby": "Id"}
        if filters:
            params["$filter"] = " and ".join(filters)
        result = self.collection(code, params, paged=True)
        records = result["records"]
        if records:
            required = {"Id", "IndicatorCode", "SpatialDim", "TimeDim"}
            if any(not required.issubset(row) or row["IndicatorCode"] != code for row in records):
                raise GHOError("invalid_response", "WHO observation schema or indicator code differs from the request.")
            scalar_fields = required | {"Value", "NumericValue", "Low", "High", "Dim1", "Dim2", "Dim3"}
            if any(isinstance(row.get(field), (dict, list)) for row in records for field in scalar_fields):
                raise GHOError("invalid_response", "WHO returned a non-scalar observation field.")
            ids = [row["Id"] for row in records if row["Id"] is not None]
            if len(set(ids)) != len(ids):
                raise GHOError("incomplete_data", "Repeated observation IDs detected, possibly overlapping pages; retry.")
            result["status"] = "ok"
        elif filters:
            probe = self.collection(code, {"$top": 1, "$select": "Id"})
            result["status"] = "filters_no_data" if probe["records"] else "indicator_no_data"
            result["baseline_probe"] = probe["provenance"]
        else:
            result["status"] = "indicator_no_data"
        result["indicator"] = entry
        result["query"] = {"indicator": code, "locations": locations, "spatial_type": spatial_type,
                           "year_from": year_from, "year_to": year_to, "dimensions": selected}
        return result


def get_gho_data(indicator, locations=None, year_from=None, year_to=None,
                 dimensions=None, *, spatial_type=None, client=None):
    return (client or GHOClient()).get_gho_data(indicator, locations, year_from,
                                               year_to, dimensions, spatial_type)
