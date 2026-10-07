"""Public xMart GHO adapter, aligned to the pinned DSIR 0.11.0 source.

Directory URLs are untrusted metadata. Only DATA_/RELAY object identifiers
are extracted; every request stays on the configured production transport.
"""
from __future__ import annotations

import re
import time
import math
from urllib.parse import unquote

from gho_client import GHOError, literal
from clean import _as_integer, _as_number, _as_string

DIRECTORY_FIELDS = (
    "IND_ID", "IND_PER_CODE", "IND_CODE_GHO", "IND_NAME_FULL", "IND_NAME",
    "TERM_LANG", "IND_UNIT", "IND_PUBLISH_TABLE", "DWNL_QUERY",
)
REGIONS = {"AFR": "953", "AMR": "954", "SEAR": "955", "EUR": "956",
           "EMR": "957", "WPR": "958", "GLOBAL": "001"}
SEX = {"SEX_BTSX": "TOTAL", "SEX_MLE": "MALE", "SEX_FMLE": "FEMALE"}
SEX_INVERSE = {v: k for k, v in SEX.items()} | {"BTSX": "SEX_BTSX", "MLE": "SEX_MLE", "FMLE": "SEX_FMLE"}
EXCLUDED_DIMENSIONS = {"DIM_TIME", "DIM_TIME_TYPE", "DIM_GEO_CODE_M49",
                       "DIM_GEO_CODE_TYPE", "DIM_PUBLISH_STATE_CODE", "DIM_VALUE_TYPE"}
SPATIAL_TYPES = {
    "COUNTRY": ("COUNTRY", "NATIONAL LIBERATION MOVEMENT", "ORGANIZED, UNINCORPORATED TERRITORY", "TERRITORY"),
    "REGION": ("REGION", "WHO_REGION", "WHOREGION"), "GLOBAL": ("GLOBAL", "WORLD"),
}


def in_filter(field, values):
    if len(values) == 1:
        return f"({field} eq {literal(values[0])})"
    return f"({field} in ({','.join(map(literal, values))}))"


def codes(values):
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple)) or not values or any(not isinstance(x, str) or not x for x in values):
        raise GHOError("invalid_query", "Dimension filters require nonempty source code lists.")
    return list(dict.fromkeys(values))


def dimension_fields(fields):
    fields = {f for f in fields if f.startswith("DIM_") and f not in EXCLUDED_DIMENSIONS
              and not re.fullmatch(r"DIM_(?:[0-9]+|MEMBER_?[0-9]+)_CODE", f)}
    return [f for f in ("DIM_SEX", "DIM_AGE") if f in fields] + sorted(fields - {"DIM_SEX", "DIM_AGE"})


def member_field(type_field, fields):
    field = type_field.replace("DIM_", "DIM_MEMBER_", 1)
    return field if field in fields else field.replace("DIM_MEMBER_", "DIM_MEMBER", 1)


def dimension_type(field):
    if field in {"DIM_SEX", "DIM_POP_SEX", "SEX"}:
        return "SEX"
    if field in {"DIM_AGE", "DIM_POP_AGE_GRP", "AGEGROUP"}:
        return "AGEGROUP"
    return field


def positional_value(field, value):
    kind = dimension_type(field)
    if kind == "SEX":
        return SEX_INVERSE.get(value, value)
    if kind == "AGEGROUP" and value is not None and not value.startswith("AGEGROUP_"):
        return "AGEGROUP_" + value
    return value


def numeric_display(value):
    """R as.character numeric formatting (15 significant digits, scipen=0)."""
    if value is None:
        return None
    if value == 0:
        return "0"
    exponent = math.floor(math.log10(abs(value)))
    fixed = format(value, f".{max(0, 14 - exponent)}f")
    if "." in fixed:
        fixed = fixed.rstrip("0").rstrip(".")
    mantissa, power = format(value, ".14e").split("e")
    scientific = mantissa.rstrip("0").rstrip(".") + "e" + power
    return scientific if len(scientific) < len(fixed) else fixed


class XMartAdapter:
    def __init__(self, client):
        self.client = client
        self.cache = {}

    @staticmethod
    def matches_named_dimension(row, field, allowed):
        if "DIM_1_CODE" not in row:
            return row.get(field) in allowed
        return any(value == field and row.get(member_field(position, row)) in allowed
                   for position, value in row.items()
                   if re.fullmatch(r"DIM_[0-9]+_CODE", position))

    def cached(self, key, fetch):
        saved = self.cache.get(key)
        if saved and time.monotonic() - saved[0] < 600:
            return saved[1]
        value = fetch()
        if value:
            self.cache[key] = (time.monotonic(), value)
        return value

    def directory(self):
        def fetch():
            result = self.client.collection("DATA_/IND_DIRECTORY_WIDE", {
                "$filter": "TERM_LANG eq 'en'", "$select": ",".join(DIRECTORY_FIELDS),
                "$orderby": "IND_ID,IND_PER_CODE"}, paged=True)
            rows = result["records"]
            if not rows or any(not set(DIRECTORY_FIELDS).issubset(row) for row in rows):
                raise GHOError("invalid_catalogue", "xMart indicator directory is empty or malformed.")
            keys = [(r["IND_ID"], r["IND_PER_CODE"]) for r in rows]
            if any(any(isinstance(v, (dict, list)) for v in r.values()) for r in rows) or len(set(keys)) != len(keys):
                raise GHOError("invalid_catalogue", "xMart directory contains malformed or duplicate identifiers.")
            self.directory_provenance = result["provenance"]
            return rows
        return self.cached("directory", fetch)

    def catalogue(self):
        result, seen = [], set()
        for row in self.directory():
            code = row["IND_CODE_GHO"]
            if code is None or code == "":
                continue
            name = row["IND_NAME_FULL"] or row["IND_NAME"]
            if not isinstance(code, str) or not isinstance(name, str) or not name:
                raise GHOError("invalid_catalogue", "xMart indicator code/name is malformed.")
            if code in seen:
                continue
            seen.add(code)
            result.append({"IndicatorCode": code, "IndicatorName": name,
                           "Language": str(row["TERM_LANG"]).upper(), "Unit": row["IND_UNIT"],
                           "MetadataSource": self.client.url("DATA_/IND_DIRECTORY_WIDE", {
                               "$filter": in_filter("IND_CODE_GHO", [code])})})
        if not result:
            raise GHOError("invalid_catalogue", "xMart directory supplied no GHO indicator codes.")
        self.client._catalogue = result
        return result

    def route(self, indicator):
        entry = self.client.confirm_indicator(indicator)
        indicator = entry["IndicatorCode"]
        rows = [row for row in self.directory() if row["IND_CODE_GHO"] == indicator]
        rows.sort(key=lambda row: (not bool(row["DWNL_QUERY"]), row["IND_PER_CODE"] != indicator))
        for row in rows:
            for candidate in (row["DWNL_QUERY"], row["IND_PUBLISH_TABLE"]):
                match = re.search(r"DATA_/(?:data/)?[A-Za-z0-9_]+", candidate or "")
                if not match:
                    continue
                path = match.group().replace("/data/", "/")
                if not re.fullmatch(r"DATA_/RELAY[A-Za-z0-9_]*", path):
                    continue
                return {"path": path, "id": row["IND_ID"], "code": indicator,
                        "name": row["IND_NAME_FULL"], "unit": row["IND_UNIT"],
                        "directory_record": dict(row), "catalogue_entry": entry}
        raise GHOError("unsupported_indicator_route", "The public xMart directory has no supported GHO RELAY route.", indicator=indicator)

    def fields(self, path):
        def fetch():
            result = self.client.collection(path, {"$top": 1})
            if not result["records"]:
                raise GHOError("invalid_response", "xMart table schema probe returned no record.", table=path)
            return list(result["records"][0])
        return self.cached("fields:" + path, fetch)

    def geo(self):
        def fetch():
            required = {"GEO_CODE_M49", "GEO_CODE_ISO_3", "GEO_TYPE", "GEO_NAME_SHORT"}
            rows = self.client.collection("DATA_/REF_GEO", {"$select": ",".join(sorted(required)),
                                          "$orderby": "Sys_PK"}, paged=True)["records"]
            if (not rows or any(not required.issubset(r) for r in rows)
                    or any(any(isinstance(r[f], (dict, list)) for f in required) for r in rows)):
                raise GHOError("invalid_response", "xMart geography reference is empty or malformed.")
            return rows
        return self.cached("geo", fetch)

    def geo_code(self, code, inverse=False):
        geo = self.geo()
        if inverse:
            for region, m49 in REGIONS.items():
                if code == m49:
                    return region
            found = next((r for r in geo if r["GEO_CODE_M49"] == code), None)
            return (found["GEO_CODE_ISO_3"] or code) if found else code
        found = next((r for r in geo if r["GEO_CODE_ISO_3"] == code), None)
        value = found["GEO_CODE_M49"] if found else None
        if any(r["GEO_CODE_M49"] == code for r in geo):
            value = code
        if code in REGIONS and any(r["GEO_CODE_M49"] == REGIONS[code] for r in geo):
            value = REGIONS[code]
        return value

    def dimension_values(self, dimension):
        if dimension in SPATIAL_TYPES:
            output = []
            for row in self.geo():
                code = self.geo_code(row["GEO_CODE_M49"], inverse=True)
                known_group = "GLOBAL" if code == "GLOBAL" else "REGION" if code in REGIONS else None
                if known_group == dimension or row["GEO_TYPE"] in SPATIAL_TYPES[dimension]:
                    output.append({"Code": code, "Title": row["GEO_NAME_SHORT"],
                                   "M49": row["GEO_CODE_M49"], "ParentCode": None})
            return output
        def fetch():
            required = {"TERM_SET", "TERM_KEY", "TERM_NAME_MAIN"}
            rows = self.client.collection("DATA_/REF_DISAGGREGATIONS", {
                "$select": ",".join(sorted(required)), "$orderby": "TERM_SET,TERM_KEY"}, paged=True)["records"]
            if any(not required.issubset(r) for r in rows):
                raise GHOError("invalid_response", "Malformed xMart disaggregation reference.")
            return rows
        rows = self.cached("disaggregations", fetch)
        return [{"Code": positional_value(r["TERM_SET"], r["TERM_KEY"]), "NativeCode": r["TERM_KEY"],
                 "Title": r["TERM_NAME_MAIN"]} for r in rows if dimension_type(r["TERM_SET"]) == dimension_type(dimension)]

    def long_types(self, context):
        def fetch():
            positions = [f for f in context["fields"] if re.fullmatch(r"DIM_[0-9]+_CODE", f)]
            output = {}
            for start in range(0, len(positions), 6):
                batch = positions[start:start + 6]
                rows = self.client.collection(context["path"], {"$filter": in_filter("IND_ID", [context["id"]])}, group=batch)["records"]
                for field in batch:
                    output[field] = sorted({r[field] for r in rows if r.get(field) is not None})
            return output
        return self.cached("types:" + context["path"] + ":" + str(context["id"]), fetch)

    def context(self, indicator, locations=None, year_from=None, year_to=None, dimensions=None, spatial_type=None):
        from locations import resolve_locations
        for name, value in (("year_from", year_from), ("year_to", year_to)):
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 9999):
                raise GHOError("invalid_query", f"{name} must be an integer year from 1 to 9999.")
        if year_from is not None and year_to is not None and year_from > year_to:
            raise GHOError("invalid_query", "year_from must not exceed year_to.")
        if dimensions is not None and not isinstance(dimensions, dict):
            raise GHOError("invalid_query", "dimensions must be a mapping of positions or exact named xMart fields.")
        selected = {key: codes(value) for key, value in (dimensions or {}).items()}
        if spatial_type is not None:
            spatial_type = str(spatial_type).upper()
            if spatial_type not in SPATIAL_TYPES:
                raise GHOError("invalid_query", "spatial_type must be COUNTRY, REGION or GLOBAL.")
        if locations is not None:
            locations = codes(locations)
            resolved = resolve_locations(locations, client=self.client)
            if resolved["status"] != "ok":
                raise GHOError(resolved["status"], "Location resolution requires clarification.", resolution=resolved)
            types = {r["spatial_type"].upper() for r in resolved["locations"]}
            if len(types) != 1 or spatial_type is not None and types != {spatial_type}:
                raise GHOError("invalid_query", "Query one spatial type and use matching locations.")
            spatial_type = types.pop()
            locations = [r["code"] for r in resolved["locations"]]
        route = self.route(indicator)
        fields = self.fields(route["path"])
        if not {"IND_ID", "DIM_TIME", "DIM_GEO_CODE_M49"}.issubset(fields):
            raise GHOError("invalid_response", "Unsupported xMart observation schema.", table=route["path"])
        route.update(fields=fields, dimensions=dimension_fields(fields))
        filters = [in_filter("IND_ID", [route["id"]])]
        if spatial_type:
            if "DIM_GEO_CODE_TYPE" not in fields:
                raise GHOError("invalid_response", "Requested spatial type is absent from the xMart schema.")
            filters.append(in_filter("DIM_GEO_CODE_TYPE", SPATIAL_TYPES[spatial_type]))
        if locations is not None:
            m49 = [self.geo_code(code) for code in locations]
            if any(code is None for code in m49):
                raise GHOError("unknown_location", "Requested location is absent from the live xMart geography reference.")
            filters.append(in_filter("DIM_GEO_CODE_M49", m49))
        if year_from is not None:
            filters.append(f"DIM_TIME ge '{year_from}'")
        if year_to is not None:
            filters.append(f"DIM_TIME le '{year_to}'")
        long = "DIM_1_CODE" in fields
        for key, values in selected.items():
            if key in {"dim1", "dim2", "dim3"}:
                position = int(key[-1])
                if long:
                    type_field = f"DIM_{position}_CODE"
                    member = f"DIM_MEMBER_{position}_CODE"
                    if type_field not in fields or member not in fields:
                        raise GHOError("invalid_query", "Requested dimension position is absent.", dimension=key)
                    clauses = []
                    for value in values:
                        if value in SEX:
                            clauses.append("(" + in_filter(type_field, ["DIM_SEX", "SEX"]) + " and " + in_filter(member, [SEX[value]]) + ") or (" + in_filter(type_field, ["DIM_POP_SEX"]) + " and " + in_filter(member, [value.removeprefix("SEX_")]) + ")")
                        elif value.startswith("AGEGROUP_"):
                            clauses.append("(" + in_filter(type_field, ["DIM_AGE", "AGEGROUP", "DIM_POP_AGE_GRP"]) + " and " + in_filter(member, [value.removeprefix("AGEGROUP_")]) + ")")
                        else:
                            clauses.append(in_filter(member, [value]))
                    filters.append("(" + " or ".join(clauses) + ")")
                else:
                    if position > len(route["dimensions"]):
                        raise GHOError("invalid_query", "Requested dimension position is absent.", dimension=key)
                    field = route["dimensions"][position - 1]
                    native = [SEX.get(v, v) if field == "DIM_SEX" else v.removeprefix("AGEGROUP_") if field == "DIM_AGE" else v for v in values]
                    filters.append(in_filter(field, native))
            elif long:
                positions = [field for field, types in self.long_types(route).items() if key in types]
                if not positions:
                    raise GHOError("invalid_query", "Unknown named dimension for this xMart indicator.", dimension=key)
                clauses = []
                for field in positions:
                    member = member_field(field, fields)
                    if member not in fields:
                        raise GHOError("invalid_response", "Named dimension has no corresponding member field.")
                    clauses.append("(" + in_filter(field, [key]) + " and " + in_filter(member, values) + ")")
                filters.append("(" + " or ".join(clauses) + ")")
            else:
                if key not in route["dimensions"]:
                    raise GHOError("invalid_query", "Unknown named dimension for this xMart table.", dimension=key)
                filters.append(in_filter(key, values))
        route["filter"] = " and ".join(filters)
        route["query"] = {"indicator": route["code"], "locations": locations, "spatial_type": spatial_type,
                          "year_from": year_from, "year_to": year_to, "dimensions": selected}
        return route

    def normalize(self, rows, context):
        if not rows:
            return []
        fields = list(rows[0])
        long = "VALUE_NUMERIC" in fields
        numeric_fields = [f for f in fields if f.endswith("_N")]
        if not long and not numeric_fields:
            raise GHOError("invalid_response", "xMart GHO rows contain no supported numeric measure family.")
        output = []
        named_long = sorted({row[f] for row in rows for f in fields
                             if re.fullmatch(r"DIM_[0-9]+_CODE", f) and isinstance(row.get(f), str)
                             and re.fullmatch(r"DIM_[A-Z_]+", row[f])})
        for row in rows:
            if not {"IND_ID", "DIM_TIME", "DIM_GEO_CODE_M49"}.issubset(row) or row["IND_ID"] != context["id"]:
                raise GHOError("invalid_response", "xMart row identity differs from the requested indicator.")
            if any(isinstance(value, (list, dict)) for value in row.values()):
                raise GHOError("invalid_response", "Non-scalar xMart GHO observation field.")
            active = [f for f in numeric_fields if row[f] is not None]
            if not long and len(active) > 1:
                raise GHOError("ambiguous_measure", "Multiple numeric measure families in a GHO row; no measure was selected.")
            measure = "VALUE_NUMERIC" if long else active[0] if active else None
            numeric = _as_number(row.get(measure))
            lower = "VALUE_NUMERIC_LOWER" if long else measure[:-2] + "_NL" if measure else None
            upper = "VALUE_NUMERIC_UPPER" if long else measure[:-2] + "_NU" if measure else None
            value = _as_string(row.get("VALUE_LABEL"))
            if value is None or value == "":
                value = numeric_display(numeric)
            spatial = _as_string(row.get("DIM_GEO_CODE_TYPE"))
            normalized_type = next((kind for kind in ("COUNTRY", "REGION") if spatial in SPATIAL_TYPES[kind]), spatial)
            result = {"Id": _as_string(row.get("_RecordID")), "IndicatorCode": context["code"],
                      "IndicatorName": context["name"], "SpatialDim": self.geo_code(_as_string(row["DIM_GEO_CODE_M49"]), inverse=True),
                      "SpatialDimType": normalized_type, "SpatialDimTypeOriginal": spatial,
                      "SpatialName": _as_string(row.get("GEO_NAME_SHORT")), "TimeDim": _as_integer(row["DIM_TIME"]),
                      "TimeDimType": _as_string(row.get("DIM_TIME_TYPE")), "TimeDimensionValue": _as_string(row["DIM_TIME"]),
                      "Value": value, "NumericValue": numeric, "Low": _as_number(row.get(lower)), "High": _as_number(row.get(upper)),
                      "Date": _as_string(row.get("Sys_CommitDateUtc")), "Unit": context["unit"], "MeasureField": measure,
                      "DataSourceDim": _as_string(row.get("VALUE_PROVENANCE")), "Comments": _as_string(row.get("VALUE_COMMENTS"))}
            for position in range(1, 4):
                if long:
                    kind = _as_string(row.get(f"DIM_{position}_CODE"))
                    member = _as_string(row.get(f"DIM_MEMBER_{position}_CODE"))
                elif position <= len(context["dimensions"]):
                    kind = context["dimensions"][position - 1]
                    member = _as_string(row.get(kind))
                    if member is None:
                        kind = None
                else:
                    kind = member = None
                result[f"Dim{position}Type"] = dimension_type(kind)
                result[f"Dim{position}"] = positional_value(kind, member)
            if long:
                result.update({field: None for field in named_long})
                for field in fields:
                    if re.fullmatch(r"DIM_[0-9]+_CODE", field):
                        kind = row[field]
                        if kind in named_long:
                            result[kind] = _as_string(row.get(member_field(field, fields)))
                extras = [f for f in fields if re.fullmatch(r"DIM_(?:[0-9]+|MEMBER_?[0-9]+)_CODE", f)]
            else:
                extras = dimension_fields(fields)
            result.update({f: _as_string(row.get(f)) for f in extras})
            output.append(result)
        return output

    def get_data(self, indicator, locations=None, year_from=None, year_to=None, dimensions=None, spatial_type=None):
        context = self.context(indicator, locations, year_from, year_to, dimensions, spatial_type)
        result = self.client.collection(context["path"], {"$filter": context["filter"], "$orderby": "Sys_PK"}, paged=True)
        native = result["records"]
        result["source_records"] = native
        result["records"] = self.normalize(native, context)
        result.update(indicator=context["catalogue_entry"], query=context["query"], status="ok" if native else "indicator_no_data")
        if not native and len(context["filter"]) > len(in_filter("IND_ID", [context["id"]])):
            baseline = self.client.collection(context["path"], {"$filter": in_filter("IND_ID", [context["id"]]),
                                              "$top": 1, "$count": "true", "$orderby": "Sys_PK"})
            count = baseline["provenance"]["declared_count"]
            if count is None or bool(baseline["records"]) != (count > 0):
                raise GHOError("incomplete_data", "Baseline probe cannot verify indicator observation availability.")
            result["status"] = "filters_no_data" if count > 0 else "indicator_no_data"
            result["baseline_probe"] = baseline["provenance"]
        result["provenance"].update(directory=self.directory_provenance, route=context["directory_record"],
                                      dimension_fields=context["dimensions"], source_fields=context["fields"])
        return result

    def indicator_dimensions(self, indicator):
        context = self.context(indicator)
        fields = (sorted({value for values in self.long_types(context).values() for value in values})
                  if "DIM_1_CODE" in context["fields"] else context["dimensions"])
        return [{"Dimension": field, "Title": None, "type": dimension_type(field)} for field in fields]
