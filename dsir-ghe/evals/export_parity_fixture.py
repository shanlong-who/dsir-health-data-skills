"""Export synthetic missing/zero cases for independent R/DSIR validation."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_ghe import Fixture, GHEClient, write_result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    fixture = Fixture()
    for row in fixture.rows:
        row["VAL_DTHS_COUNT_NUMERIC"] = None
        row["VAL_DTHS_COUNT_LOW"] = None
        row["VAL_DTHS_COUNT_HIGH"] = None
        row["VAL_DTHS_RATE100K_NUMERIC"] = 0
    client = GHEClient(transport=fixture, sleep=lambda _: None)
    result = client.get_data(area=["PHL", "NAM"], year=[2022, 2023],
                             sex=["FEMALE", "MALE"], age=["Y40T44"], cause=["10"],
                             measure=[row["code"] for row in fixture.definitions])
    result["synthetic_fixture"] = "Synthetic inputs only; not WHO observations."
    write_result(args.output_dir, result)
    print(json.dumps({"rows": result["row_count"], "synthetic": True}))
