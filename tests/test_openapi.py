from fumi.openapi import diff, example, flatten

OPENAPI = {
    "paths": {
        "/entities/{entity_id}": {
            "get": {
                "operationId": "get_entity_entities__entity_id__get",
                "tags": ["entities"],
                "parameters": [{"name": "entity_id", "in": "path", "required": True, "schema": {"type": "string"}}],
            }
        },
        "/entities": {
            "post": {
                "operationId": "create_entity_entities_post",
                "summary": "Create entity",
                "tags": ["entities"],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/EntityIn"}}},
                },
            }
        },
    },
    "components": {
        "schemas": {
            "EntityIn": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "country": {"anyOf": [{"type": "string"}, {"type": "null"}], "default": "US"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            }
        }
    },
}


def test_flatten_resolves_refs_and_names():
    ops = {o["id"]: o for o in flatten(OPENAPI)}
    get = ops["get_entity_entities__entity_id__get"]
    assert get["summary"] == "Get entity"
    assert get["params"][0]["required"] is True
    create = ops["create_entity_entities_post"]
    assert create["summary"] == "Create entity"
    assert create["body"]["fields"] == {
        "name": {"type": "string", "required": True},
        "country": {"type": "string", "required": False},
        "tags": {"type": "string[]", "required": False},
    }
    assert create["body"]["example"] == {"name": "", "country": "US", "tags": []}


def test_example_prefers_examples_and_enums():
    assert example({"type": "string", "enum": ["a", "b"]}) == "a"
    assert example({"type": "integer", "example": 7}) == 7


def test_diff_reports_added_and_removed():
    a = [{"id": "x", "method": "GET", "summary": "X"}]
    b = [{"id": "y", "method": "POST", "summary": "Y"}]
    assert diff(a, b) == {"added": [{"id": "y", "label": "POST Y"}], "removed": [{"id": "x", "label": "GET X"}]}
    assert diff(None, b) == {"added": [], "removed": []}

