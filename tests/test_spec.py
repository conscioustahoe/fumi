import json

import pytest

from fumi.spec import SpecError, read, resolve


def test_reads_openapi_3(tmp_path):
    f = tmp_path / "openapi.json"
    f.write_text(json.dumps({"openapi": "3.0.3", "paths": {}}))
    assert read(f)["openapi"] == "3.0.3"


@pytest.mark.parametrize("text, message", [
    ("{", "not valid JSON"),
    ('{"swagger": "2.0"}', "not an OpenAPI 3 document"),
    ('{"openapi": "3.1.0", "paths": []}', "not an object"),
])
def test_explains_bad_files(tmp_path, text, message):
    f = tmp_path / "openapi.json"
    f.write_text(text)
    with pytest.raises(SpecError, match=message):
        read(f)


def test_missing_file(tmp_path):
    with pytest.raises(SpecError, match="doesn't exist"):
        read(tmp_path / "gone.json")
    with pytest.raises(SpecError, match="not a file"):
        resolve(tmp_path)
