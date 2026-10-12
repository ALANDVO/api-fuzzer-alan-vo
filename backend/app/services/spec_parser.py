"""OpenAPI 3.x / Swagger specification parser and semantic schema extractor."""
import json
from typing import Any, Dict, List, Tuple
import yaml
from backend.app.models.schemas import EndpointSummary


class SpecParserError(ValueError):
    """Raised when OpenAPI specification cannot be parsed or lacks valid structure."""
    pass


def parse_raw_spec(raw_content: str) -> Dict[str, Any]:
    """Parse raw spec string formatted as JSON or YAML."""
    if not raw_content or not raw_content.strip():
        raise SpecParserError("OpenAPI specification content cannot be empty.")
    try:
        return json.loads(raw_content)
    except json.JSONDecodeError:
        try:
            parsed = yaml.safe_load(raw_content)
            if not isinstance(parsed, dict):
                raise SpecParserError("YAML document must deserialize into a root object.")
            return parsed
        except Exception as e:
            raise SpecParserError(f"Failed to parse specification as JSON or YAML: {str(e)}") from e


def extract_endpoints(spec: Dict[str, Any]) -> List[EndpointSummary]:
    """Extract normalized endpoint list with method, path, parameters, body, and expected responses."""
    endpoints: List[EndpointSummary] = []
    if not isinstance(spec, dict) or "paths" not in spec or not isinstance(spec.get("paths"), dict):
        raise SpecParserError("OpenAPI spec missing valid 'paths' dictionary.")
    paths = spec["paths"]

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        # Common path-level parameters
        common_params = path_item.get("parameters", []) if isinstance(path_item.get("parameters"), list) else []

        for method, operation in path_item.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(operation, dict):
                continue

            summary = operation.get("summary") or operation.get("description") or f"{method.upper()} {path}"
            op_params = operation.get("parameters", []) if isinstance(operation.get("parameters"), list) else []
            all_params_raw = common_params + op_params

            normalized_params: List[Dict[str, Any]] = []
            for p in all_params_raw:
                if not isinstance(p, dict):
                    continue
                schema = p.get("schema", {})
                normalized_params.append({
                    "name": p.get("name", "param"),
                    "in": p.get("in", "query"),
                    "required": bool(p.get("required", False)),
                    "schema": schema if isinstance(schema, dict) else {"type": "string"},
                })

            # Extract request body schema (OpenAPI 3.x)
            body_schema = None
            req_body = operation.get("requestBody")
            if isinstance(req_body, dict):
                content = req_body.get("content", {})
                if isinstance(content, dict):
                    json_media = content.get("application/json", {})
                    if isinstance(json_media, dict):
                        body_schema = json_media.get("schema")

            # OpenAPI 2.0 body param fallback
            if not body_schema:
                for p in all_params_raw:
                    if isinstance(p, dict) and p.get("in") == "body":
                        body_schema = p.get("schema")
                        break

            # Response status codes
            responses = []
            resps = operation.get("responses", {})
            if isinstance(resps, dict):
                responses = [str(k) for k in resps.keys()]

            endpoints.append(
                EndpointSummary(
                    method=method.upper(),
                    path=path,
                    summary=summary[:120],
                    params=normalized_params,
                    body_schema=body_schema if isinstance(body_schema, dict) else None,
                    responses=responses,
                )
            )

    return endpoints


def parse_spec_full(raw_content: str) -> Tuple[Dict[str, Any], List[EndpointSummary]]:
    """Parse raw spec content and return (spec_dict, endpoints_list)."""
    spec_dict = parse_raw_spec(raw_content)
    endpoints = extract_endpoints(spec_dict)
    return spec_dict, endpoints
