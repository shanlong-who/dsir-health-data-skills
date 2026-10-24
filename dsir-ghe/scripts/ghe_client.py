"""GHE discovery and observation semantics aligned with DSIR 0.11.0."""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import unicodedata
from pathlib import Path

from transport import BASE_URL, TABLE, GHEError, Transport, utc_now

METADATA = Path(__file__).resolve().parents[1] / "references" / "metadata"
KEYS = ["Sys_PK", "DIM_COUNTRY_CODE", "DIM_YEAR_CODE", "DIM_SEX_CODE",
        "DIM_AGEGROUP_CODE", "DIM_GHECAUSE_CODE", "DIM_GHECAUSE_TITLE",
        "ATTR_POPULATION_NUMERIC", "FLAG_LEVEL", "DIM_CAUSE_GROUP", "FLAG_RANKABLE"]
DATA_FIELDS = ("iso3", "location_name", "year", "sex", "age", "cause_code", "cause_name",
               "measure", "value", "low", "high", "population", "unit", "level", "cause_group", "rankable")
CAUSE_FIELDS = ["DIM_GHECAUSE_CODE", "DIM_GHECAUSE_TITLE", "FLAG_LEVEL", "DIM_CAUSE_GROUP",
                "FLAG_RANKABLE", "FLAG_SINGLE_CAUSE"]
METHODS_URL = "https://www.who.int/data/global-health-estimates"


def load_reference():
    provenance = json.loads((METADATA / "provenance.json").read_text(encoding="utf-8"))
    result = {}
    for name in ("who_countries", "measures"):
        content = (METADATA / f"{name}.json").read_bytes()
        if hashlib.sha256(content).hexdigest() != provenance["files"][name]:
            raise GHEError("reference_integrity_failed", "Bundled DSIR reference does not match its checksum.")
        result[name] = json.loads(content)
    countries = result["who_countries"]
    if len(countries) != 194 or len({row["iso3"] for row in countries}) != 194:
        raise GHEError("reference_integrity_failed", "Bundled WHO country mapping is invalid.")
    return result, provenance


def codes(values, name, numeric=False):
    if values is None:
        return None
    if isinstance(values, (str, int)) and not isinstance(values, bool):
        values = [values]
    if not isinstance(values, (list, tuple)) or not values:
        raise GHEError("invalid_query", f"{name} requires a nonempty code list.")
    output = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (str, int)) or not str(value):
            raise GHEError("invalid_query", f"{name} contains an invalid code.")
        value = str(value)
        if not re.fullmatch(r"(?:0|[1-9][0-9]*)" if numeric else r"[A-Za-z0-9_.-]+", value):
            raise GHEError("invalid_query", f"{name} requires exact source codes.", value=value)
        if value not in output:
            output.append(value)
    return output


def years(values, name):
    if values is None:
        return None
    values = values if isinstance(values, (list, tuple)) else [values]
    if not values or any(isinstance(value, bool) or not isinstance(value, int)
                         or not 0 <= value <= 9999 for value in values):
        raise GHEError("invalid_query", f"{name} requires integer years.")
    return list(dict.fromkeys(values))


def in_filter(field, values, numeric=False):
    if values is None:
        return None
    literals = [str(value) if numeric else "'" + str(value).replace("'", "''") + "'" for value in values]
    return (f"({field} eq {literals[0]})" if len(literals) == 1 else
            f"({field} in ({','.join(literals)}))")


def numeric(value, field, integer=False):
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise GHEError("invalid_response", "Invalid numeric observation field.", field=field)
    try:
        number = float(value)
    except ValueError as exc:
        raise GHEError("invalid_response", "Nonnumeric text in a numeric GHE field.", field=field) from exc
    if not math.isfinite(number) or integer and number != int(number):
        raise GHEError("invalid_response", "Nonfinite or noninteger GHE field.", field=field)
    return int(number) if integer else number


def flag(value):
    if value is None:
        return None
    if value not in (True, False, 0, 1) or isinstance(value, str):
        raise GHEError("invalid_response", "Invalid GHE logical flag.")
    return bool(value)


class GHEClient:
    def __init__(self, **transport_options):
        self.http = Transport(**transport_options)
        self.reference, self.reference_provenance = load_reference()
        self.countries = {row["iso3"]: row for row in self.reference["who_countries"]}
        self.cache = {}

    def cached(self, key, fetch):
        saved = self.cache.get(key)
        if saved and time.monotonic() - saved[0] < 600:
            return saved[1]
        result = fetch()
        self.cache[key] = (time.monotonic(), result)
        return result

    def fields(self):
        def fetch():
            rows = self.http.records(self.http.request(TABLE, {"$top": 1}))
            if len(rows) != 1 or not set(KEYS).issubset(rows[0]):
                raise GHEError("invalid_response", "Unsupported or empty GHE observation schema.")
            return set(rows[0])
        return self.cached("fields", fetch)

    def latest(self):
        return max(int(row["code"]) for row in self.dimensions("year"))

    def reference_area(self):
        available = sorted(row["code"] for row in self.dimensions("area") if row["code"] in self.countries)
        if not available:
            raise GHEError("invalid_catalogue", "No WHO Member State is available for the GHE reference slice.")
        return available[0]

    def dimensions(self, dimension="measure"):
        if dimension == "cause":
            return self.causes()
        if dimension not in {"measure", "area", "year", "sex", "age"}:
            raise GHEError("invalid_query", "Unknown GHE dimension.", dimension=dimension)
        def fetch():
            if dimension == "measure":
                return [dict(row) for row in self.reference["measures"] if row["field"] in self.fields()]
            if dimension in {"year", "sex"}:
                name, top = ("YEAR", 100) if dimension == "year" else ("SEX", 20)
                source = self.http.reference(f"DEX_CMS/REF_{name}_COD", top)
                if dimension == "year":
                    return [{"code": str(numeric(row["CODE"], "CODE", integer=True)),
                             "label": str(numeric(row["CODE"], "CODE", integer=True))} for row in source]
                return [{"code": str(row["CODE"]), "label": row["TITLE"]} for row in source]
            selection = f"DIM_YEAR_CODE eq {self.latest()} and DIM_GHECAUSE_CODE eq 0 and DIM_SEX_CODE eq 'TOTAL'"
            field = "DIM_COUNTRY_CODE" if dimension == "area" else "DIM_AGEGROUP_CODE"
            if dimension == "area":
                selection += " and DIM_AGEGROUP_CODE eq 'TOTAL'"
                labels = {code: row["name_short"] for code, row in self.countries.items()}
            else:
                selection += f" and DIM_COUNTRY_CODE eq '{self.reference_area()}'"
                labels = {str(row["CODE"]): row["TITLE"] for row in self.http.reference("DEX_CMS/REF_AGE_COD", 100)}
            rows = self.http.collection(selection, ["Sys_PK", field])["records"]
            if not rows or any(not isinstance(row[field], str) or not row[field] for row in rows):
                raise GHEError("invalid_catalogue", "GHE dimension reference slice is empty or malformed.")
            return [{"code": code, "label": labels.get(code)} for code in sorted({row[field] for row in rows})]
        result = self.cached("dimension:" + dimension, fetch)
        if not result:
            raise GHEError("invalid_catalogue", "No supported codes could be established.", dimension=dimension)
        return result

    def causes(self, search=None):
        def fetch():
            selection = (f"DIM_YEAR_CODE eq {self.latest()} and DIM_AGEGROUP_CODE eq 'TOTAL' "
                         f"and DIM_SEX_CODE eq 'TOTAL' and DIM_COUNTRY_CODE eq '{self.reference_area()}'")
            rows = self.http.collection(selection, ["Sys_PK", *CAUSE_FIELDS])["records"]
            if not rows:
                raise GHEError("invalid_catalogue", "GHE cause reference slice is empty.")
            result = [{"cause_code": str(numeric(row["DIM_GHECAUSE_CODE"], "cause", integer=True)),
                       "cause_name": row["DIM_GHECAUSE_TITLE"], "level": numeric(row["FLAG_LEVEL"], "level", integer=True),
                       "cause_group": None if row["DIM_CAUSE_GROUP"] is None else str(row["DIM_CAUSE_GROUP"]),
                       "rankable": flag(row["FLAG_RANKABLE"]), "single_cause": flag(row["FLAG_SINGLE_CAUSE"])}
                      for row in rows]
            if any(row["cause_code"] == "None" for row in result) or len({r["cause_code"] for r in result}) != len(result):
                raise GHEError("invalid_catalogue", "Missing or duplicate GHE cause identifiers.")
            return result
        result = self.cached("causes", fetch)
        if search is None:
            return result
        if not isinstance(search, str) or not search.strip():
            raise GHEError("invalid_query", "Cause search requires words.")
        terms = search.casefold().split()
        return [row for row in result if all(term in (row["cause_name"] or "").casefold() for term in terms)]

    def locations(self, names):
        if not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise GHEError("invalid_query", "Supply location names or codes.")
        normalize = lambda text: " ".join(unicodedata.normalize("NFKC", text).casefold().split())
        available = {row["code"]: row for row in self.dimensions("area")}
        index = {}
        for code in available:
            index.setdefault(normalize(code), set()).add(code)
        for code, row in self.countries.items():
            if code in available:
                for key in ("iso3", "iso2", "m49_code", "name_short", "name_official"):
                    index.setdefault(normalize(row[key]), set()).add(code)
                index.setdefault(str(int(row["m49_code"])), set()).add(code)
        resolved, unresolved = [], []
        for name in names:
            hits = sorted(index.get(normalize(name), set()))
            if len(hits) == 1:
                resolved.append({"input": name, **available[hits[0]]})
            else:
                unresolved.append({"input": name, "candidates": [available[code] for code in hits],
                                   "reason": "ambiguous" if hits else "unrecognized"})
        return {"status": "needs_clarification" if unresolved else "ok",
                "locations": resolved, "unresolved": unresolved}

    def validate_selection(self, *, area=None, year=None, year_from=None, year_to=None,
                           sex=None, age=None, cause=None, measure=None, coverage=False):
        selected = {name: codes(value, name, numeric=name == "cause") for name, value in
                    (("area", area), ("sex", sex), ("age", age), ("cause", cause), ("measure", measure))}
        if any(selected[name] is None for name in ("area", "sex", "age", "cause")):
            raise GHEError("invalid_query", "Select area, sex, age and cause explicitly; inspect dimensions first.")
        if not coverage and selected["measure"] is None:
            raise GHEError("invalid_query", "Select a measure explicitly.")
        selected["year"] = years(year, "year")
        for name, value in (("year_from", year_from), ("year_to", year_to)):
            checked = years(value, name)
            if checked is not None and len(checked) != 1:
                raise GHEError("invalid_query", "Year range bounds must be scalar.")
            selected[name] = checked[0] if checked else None
        if (selected["year"] is not None and (year_from is not None or year_to is not None)
                or year_from is not None and year_to is not None and selected["year_from"] > selected["year_to"]):
            raise GHEError("invalid_query", "Supply exact years or an ordered inclusive year range.")
        catalogues = {}
        for name in ("area", "sex", "age", "year", "measure", "cause"):
            if selected[name] is None:
                continue
            catalogue = self.causes() if name == "cause" else self.dimensions(name)
            key = "cause_code" if name == "cause" else "code"
            unknown = sorted(set(map(str, selected[name])) - {row[key] for row in catalogue})
            if unknown:
                raise GHEError("invalid_query", "Code not found in the selected GHE reference catalogue.",
                               dimension=name, codes=unknown, catalogue_scope="current reference slice",
                               fallback_performed=False)
            catalogues[name] = [row for row in catalogue if row[key] in set(map(str, selected[name]))]
        filters = [in_filter("DIM_COUNTRY_CODE", selected["area"]),
                   in_filter("DIM_YEAR_CODE", selected["year"], True),
                   f"DIM_YEAR_CODE ge {selected['year_from']}" if year_from is not None else None,
                   f"DIM_YEAR_CODE le {selected['year_to']}" if year_to is not None else None,
                   in_filter("DIM_SEX_CODE", selected["sex"]), in_filter("DIM_AGEGROUP_CODE", selected["age"]),
                   in_filter("DIM_GHECAUSE_CODE", selected["cause"], True)]
        return selected, " and ".join(item for item in filters if item), catalogues

    def get_data(self, **selection):
        query, filter_text, catalogue = self.validate_selection(**selection)
        measures = [next(row for row in catalogue["measure"] if row["code"] == code) for code in query["measure"]]
        fields = list(KEYS)
        for definition in measures:
            field = definition["field"]
            fields.append(field)
            if field.endswith("_COUNT_NUMERIC"):
                fields.extend(bound for bound in (field.removesuffix("_NUMERIC") + "_LOW",
                                                 field.removesuffix("_NUMERIC") + "_HIGH") if bound in self.fields())
        result = self.http.collection(filter_text, fields)
        data, context = [], []
        for index, row in enumerate(result["records"]):
            self.check_row_selection(row, query)
            for definition in measures:
                field, measure = definition["field"], definition["code"]
                is_count = field.endswith("_COUNT_NUMERIC")
                data.append({
                    "iso3": row["DIM_COUNTRY_CODE"], "location_name": self.countries.get(row["DIM_COUNTRY_CODE"], {}).get("name_short"),
                    "year": numeric(row["DIM_YEAR_CODE"], "year", True), "sex": row["DIM_SEX_CODE"],
                    "age": row["DIM_AGEGROUP_CODE"], "cause_code": str(numeric(row["DIM_GHECAUSE_CODE"], "cause", True)),
                    "cause_name": row["DIM_GHECAUSE_TITLE"], "measure": measure, "value": numeric(row[field], field),
                    "low": numeric(row.get(field.removesuffix("_NUMERIC") + "_LOW"), "low") if is_count else None,
                    "high": numeric(row.get(field.removesuffix("_NUMERIC") + "_HIGH"), "high") if is_count else None,
                    "population": numeric(row["ATTR_POPULATION_NUMERIC"], "population"), "unit": definition["unit"],
                    "level": numeric(row["FLAG_LEVEL"], "level", True),
                    "cause_group": None if row["DIM_CAUSE_GROUP"] is None else str(row["DIM_CAUSE_GROUP"]),
                    "rankable": flag(row["FLAG_RANKABLE"])})
                context.append({"raw_row_index": index, "source_row_id": row["Sys_PK"], "provider_field": field,
                                "rate_type": ("crude" if row["DIM_AGEGROUP_CODE"] == "TOTAL" else "age_specific")
                                if measure.endswith("_rate") else None})
        ordering = sorted(range(len(data)), key=lambda index: tuple(data[index][key] for key in
                          ("iso3", "year", "sex", "age", "cause_code", "measure")))
        data, context = [data[i] for i in ordering], [context[i] for i in ordering]
        for index, row in enumerate(context):
            row["clean_row_index"] = index
        qa = self.qa(data)
        coverage = self.coverage_rows(result["records"], query["area"])
        absent = [row["location"] for row in coverage if not row["source_rows"]]
        if data and absent:
            qa["issues"].append({"severity": "warning", "code": "locations_without_data",
                                 "locations": absent, "message": "No matching source rows for some selected locations."})
            if qa["status"] == "pass":
                qa["status"] = "warning"
        provenance = {**result["provenance"], "requests": list(self.http.trace), "release": None,
                      "estimate_type": "WHO GHE estimates", "method_context_url": METHODS_URL,
                      "method_context_establishes_api_release": False,
                      "dsir_reference": self.reference_provenance, "automatic_fallback": False}
        return {"schema_version": "0.1.0", "status": "qa_failed" if qa["status"] == "fail" else
                "ok" if data else "filters_no_data", "query": query, "catalogue": catalogue,
                "row_count": len(data), "data": data, "observation_context": context,
                "coverage_by_location": coverage,
                "qa": qa, "provenance": provenance, "raw": result["records"],
                "limitations": [
                    "The API response does not establish a release identifier; retrieval time is not release time.",
                    "GHE estimates synthesize multiple sources; they are not raw registered deaths.",
                    "All-age rates are crude, selected-age rates are age-specific; no age standardization is performed.",
                    "Do not sum rates, overlapping ages, cause totals and components, or assume cause_group is a parent code.",
                    "Country labels and groupings use the bundled, dated DSIR snapshot; source availability is checked live."]}

    @staticmethod
    def check_row_selection(row, query):
        for key, field in (("area", "DIM_COUNTRY_CODE"), ("sex", "DIM_SEX_CODE"),
                           ("age", "DIM_AGEGROUP_CODE"), ("cause", "DIM_GHECAUSE_CODE")):
            value = str(numeric(row.get(field), field, True)) if key == "cause" else row.get(field)
            if value not in query[key]:
                raise GHEError("invalid_response", "Provider returned a row outside the selected dimensions.", field=field)
        year = numeric(row.get("DIM_YEAR_CODE"), "year", True)
        if (year is None or query["year"] is not None and year not in query["year"]
                or query["year_from"] is not None and year < query["year_from"]
                or query["year_to"] is not None and year > query["year_to"]):
            raise GHEError("invalid_response", "Provider returned an observation outside the selected years.")

    @staticmethod
    def coverage_rows(rows, areas):
        return [{"location": area, "years": sorted({numeric(row["DIM_YEAR_CODE"], "year", True)
                  for row in rows if row["DIM_COUNTRY_CODE"] == area}),
                 "source_rows": sum(row["DIM_COUNTRY_CODE"] == area for row in rows)} for area in areas]

    def coverage(self, **selection):
        query, filter_text, catalogue = self.validate_selection(**selection, coverage=True)
        fields = ["Sys_PK", "DIM_COUNTRY_CODE", "DIM_YEAR_CODE", "DIM_SEX_CODE", "DIM_AGEGROUP_CODE", "DIM_GHECAUSE_CODE"]
        result = self.http.collection(filter_text, fields)
        for row in result["records"]:
            self.check_row_selection(row, query)
        coverage = self.coverage_rows(result["records"], query["area"])
        return {"status": "ok" if result["records"] else "filters_no_data", "query": query,
                "catalogue": catalogue, "coverage_by_location": coverage, "raw": result["records"],
                "provenance": {**result["provenance"], "requests": list(self.http.trace), "release": None},
                "note": "Counts are source observations before measure pivoting, not deaths or nonmissing estimates."}

    @staticmethod
    def qa(data):
        issues, seen = [], set()
        for row in data:
            key = tuple(row[field] for field in ("iso3", "year", "sex", "age", "cause_code", "measure"))
            if key in seen:
                issues.append({"severity": "error", "code": "duplicate_observation", "message": "Repeated measure and stratum; rows retained for inspection."})
            seen.add(key)
            if any(row[field] is not None and row[field] < 0 for field in ("value", "low", "high", "population")):
                issues.append({"severity": "error", "code": "negative_value", "message": "Unexpected negative GHE value."})
            if row["measure"].endswith("_percent") and row["value"] is not None and row["value"] > 100:
                issues.append({"severity": "error", "code": "percentage_out_of_range", "message": "GHE percentage exceeds 100."})
            if row["low"] is not None and row["high"] is not None and row["low"] > row["high"]:
                issues.append({"severity": "error", "code": "reversed_interval", "message": "Lower bound exceeds upper bound."})
            if row["value"] is not None and ((row["low"] is not None and row["value"] < row["low"])
                                            or (row["high"] is not None and row["value"] > row["high"])):
                issues.append({"severity": "warning", "code": "value_outside_interval", "message": "Source estimate is outside its bounds."})
        missing = sum(row["value"] is None for row in data)
        if missing:
            issues.append({"severity": "warning", "code": "missing_values", "message": f"{missing} selected measure values are missing; not zero."})
        return {"status": "fail" if any(item["severity"] == "error" for item in issues) else
                "warning" if issues else "pass", "issues": issues, "missing_numeric": missing}
