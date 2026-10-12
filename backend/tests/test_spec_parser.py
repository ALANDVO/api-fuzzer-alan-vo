"""Tests covering OpenAPI parsing, YAML support, parameter and body extraction."""
import json
import pytest
from backend.app.services.spec_parser import SpecParserError, extract_endpoints, parse_raw_spec, parse_spec_full

SAMPLE_OPENAPI_JSON = json.dumps({
    "openapi": "3.0.0",
    "info": {"title": "Pet Store API", "version": "1.0.0"},
    "paths": {
        "/pets": {
            "get": {
                "summary": "List all pets",
                "parameters": [
                    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}}
                ],
                "responses": {"200": {"description": "OK"}}
            },
            "post": {
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}, "tag": {"type": "string"}}
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}, "400": {"description": "Bad Request"}}
            }
        },
        "/pets/{id}": {
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
            ],
            "get": {
                "summary": "Get pet by ID",
                "responses": {"200": {"description": "OK"}, "404": {"description": "Not Found"}}
            }
        }
    }
})

SAMPLE_OPENAPI_YAML = """
openapi: 3.0.1
info:
  title: Users Service
  version: 2.1.0
paths:
  /users:
    get:
      summary: Retrieve users
      responses:
        '200':
          description: OK
"""


def test_parse_valid_json_spec():
    spec, endpoints = parse_spec_full(SAMPLE_OPENAPI_JSON)
    assert spec["info"]["title"] == "Pet Store API"
    assert len(endpoints) == 3

    get_pets = next(e for e in endpoints if e.path == "/pets" and e.method == "GET")
    assert len(get_pets.params) == 1
    assert get_pets.params[0]["name"] == "limit"

    post_pets = next(e for e in endpoints if e.path == "/pets" and e.method == "POST")
    assert post_pets.body_schema is not None
    assert "name" in post_pets.body_schema.get("properties", {})

    get_id = next(e for e in endpoints if e.path == "/pets/{id}" and e.method == "GET")
    assert len(get_id.params) == 1
    assert get_id.params[0]["name"] == "id"


def test_parse_valid_yaml_spec():
    spec, endpoints = parse_spec_full(SAMPLE_OPENAPI_YAML)
    assert spec["info"]["title"] == "Users Service"
    assert len(endpoints) == 1
    assert endpoints[0].path == "/users"
    assert endpoints[0].method == "GET"


def test_empty_spec_rejected():
    with pytest.raises(SpecParserError):
        parse_spec_full("")


def test_invalid_json_or_yaml_rejected():
    with pytest.raises(SpecParserError):
        parse_spec_full("{invalid json document:: 123")


def test_missing_paths_rejected():
    with pytest.raises(SpecParserError):
        extract_endpoints({"openapi": "3.0.0", "info": {"title": "Empty"}})
