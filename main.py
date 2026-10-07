#!/usr/bin/env python3
# api-fuzzer — AI-powered API fuzzer that reads an OpenAPI spec, generates adversarial test cases using LLM reasoning, executes them against a live endpoint, and reports findings with severity scores — surfacing edge cases humans miss.
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import LLM
def _load_spec(path):
    """Load OpenAPI spec (JSON or YAML)."""
    with open(path) as f:
        content = f.read()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        try:
            import yaml
            return yaml.safe_load(content)
        except ImportError:
            raise ValueError("YAML spec detected but PyYAML is not installed. pip install pyyaml")

def _endpoints_from_spec(spec):
    """Extract endpoint list with method, path, and parameter summary."""
    eps = []
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            eps.append({
                "method": method.upper(),
                "path": path,
                "summary": op.get("summary", ""),
                "params": [
                    {"name": p.get("name"), "in": p.get("in"), "required": p.get("required", False),
                     "schema": p.get("schema", {})}
                    for p in op.get("parameters", [])
                ],
                "body": (op.get("requestBody", {}).get("content", {}) or {}).get("application/json", {}).get("schema", {}),
                "responses": list((op.get("responses", {}) or {}).keys()),
            })
    return eps

def generate(args):
    """Generate adversarial test cases for an endpoint (dry run)."""
    llm = LLM()
    spec = _load_spec(args.spec)
    eps = _endpoints_from_spec(spec)
    if args.endpoint:
        eps = [e for e in eps if args.endpoint in e["path"]]
    if not eps:
        print(f"No endpoints matched {args.endpoint}")
        return []

    cases = []
    for ep in eps[:args.max_endpoints]:
        print(f"Generating cases for {ep['method']} {ep['path']}...")
        spec_blob = json.dumps({
            "method": ep["method"], "path": ep["path"], "summary": ep["summary"],
            "parameters": ep["params"], "request_schema": ep["body"], "expected_responses": ep["responses"],
        }, indent=2)

        response = llm.generate(
            f"OpenAPI endpoint specification:\n{spec_blob}\n\n"
            "Generate adversarial test cases that find bugs humans miss. Cover these attack/edge dimensions:\n"
            "1. Boundary values (min/max/empty/oversized) for every parameter\n"
            "2. Type coercion (string where int expected, null, nested objects)\n"
            "3. Injection payloads (SQLi, XSS, path traversal ../, header injection \\r\\n)\n"
            "4. Auth/permission bypass (missing token, wrong role, IDOR)\n"
            "5. Idempotency and race conditions (duplicate POST, concurrent PUT)\n"
            "6. Unicode/locale edge cases (emoji, RTL, 10k-char strings)\n\n"
            f"Generate {args.cases_per_endpoint} cases. Output a JSON array where each object is: "
            "{{\"name\": \"short test name\", \"method\": \"...\", \"path\": \"with concrete values\", "
            "\"headers\": {{}} , \"body\": ... or null, \"expected_status\": <int>, "
            "\"expected_behavior\": \"what a correct API should do\", \"dimension\": \"one of the 6 categories above\"}}",
            system="You are an API security engineer and fuzzing expert. Every case must be concrete and executable — no placeholder values. Payloads should be realistic attack strings, not 'some string'."
        )
        parsed = _parse_json_array(response)
        for c in parsed:
            c["endpoint"] = f"{ep['method']} {ep['path']}"
            cases.append(c)
        print(f"  {len(parsed)} case(s)")

    print(f"\nTotal test cases: {len(cases)}")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(cases, f, indent=2)
        print(f"Saved to {args.output}")
    return cases

def fuzz(args):
    """Generate + execute adversarial tests against a live API."""
    llm = LLM()
    base = args.base.rstrip("/")
    spec = _load_spec(args.spec)
    eps = _endpoints_from_spec(spec)
    if args.endpoint:
        eps = [e for e in eps if args.endpoint in e["path"]]
    print(f"Fuzzing {len(eps)} endpoint(s) at {base}\n")

    cases = []
    for ep in eps[:args.max_endpoints]:
        spec_blob = json.dumps({"method": ep["method"], "path": ep["path"], "summary": ep["summary"],
                               "parameters": ep["params"], "request_schema": ep["body"],
                               "expected_responses": ep["responses"]}, indent=2)
        response = llm.generate(
            f"OpenAPI endpoint specification:\n{spec_blob}\n\n"
            "Generate adversarial test cases: boundary values, type coercion, injection (SQLi/XSS/path traversal/header injection), auth bypass, race conditions, Unicode edges. "
            f"Generate {args.cases_per_endpoint} concrete executable cases. Output a JSON array of objects: "
            "{\"name\": \"...\", \"method\": \"...\", \"path\": \"...\", \"headers\": {}, \"body\": ..., \"expected_status\": <int>, \"expected_behavior\": \"...\", \"dimension\": \"...\"}",
            system="You are an API security engineer. Concrete payloads only — realistic attack strings, exact boundary values. No placeholders."
        )
        for c in _parse_json_array(response):
            c["endpoint"] = f"{ep['method']} {ep['path']}"
            cases.append(c)

    print(f"Executing {len(cases)} cases...\n")
    findings = []
    import requests
    for i, case in enumerate(cases, 1):
        url = base + case.get("path", "/")
        method = case.get("method", "GET").upper()
        headers = case.get("headers") or {}
        body = case.get("body")
        start = time.time()
        try:
            r = requests.request(method, url, headers=headers, json=body if body is not None else None, timeout=30, verify=True)
            status, rtext, err = r.status_code, r.text[:500], None
        except Exception as e:
            status, rtext, err = 0, "", str(e)[:200]
        elapsed = time.time() - start

        verdict = llm.classify(
            text=(f"Test: {case.get('name')}\nMethod: {method} {url}\nBody: {json.dumps(body) if body else 'none'}\n"
                  f"Expected: status {case.get('expected_status')} — {case.get('expected_behavior', 'correct behavior')}\n"
                  f"Actual: status {status or 'CONNECTION ERROR'}\nResponse: {rtext or err}\n\n"
                  f"Dimension: {case.get('dimension', '?')}"),
            categories=["pass", "minor", "moderate", "critical"],
            instructions="Judge the API response against the expected behavior. 'critical' = security hole, data corruption, or 500 on valid input. 'moderate' = wrong status code or malformed response. 'minor' = cosmetic deviation. 'pass' = correct. If it was a security payload and the API reflected it unescaped or returned 500, that is critical."
        )
        sev = verdict.get("category", "pass")
        if sev != "pass":
            findings.append({
                "test": case.get("name", ""), "endpoint": case.get("endpoint", ""),
                "severity": sev, "status": status, "response": rtext, "error": err,
                "reasoning": verdict.get("reasoning", "")[:300], "evidence": verdict.get("key_findings", []),
                "reproduction": f"curl -X {method} {url} " + (f"-H '{json.dumps(headers)}' " if headers else "") + (f"-d '{json.dumps(body)}' " if body else "") + "--max-time 30",
                "elapsed_ms": round(elapsed * 1000, 1),
            })
            icon = {"critical": "🔴", "moderate": "🟠", "minor": "🟡"}.get(sev, "⚪")
            print(f"  {i:>3}. {icon} [{sev.upper()}] {case.get('name', '?')} → {status or 'ERR'}")
        else:
            print(f"  {i:>3}. ✅ {case.get('name', '?')}")

    _fuzz_report(findings, len(cases), args)
    return findings

def _fuzz_report(findings, total, args):
    print(f"\n{'='*60}")
    print(f"FUZZ RESULTS: {len(findings)} finding(s) of {total} cases")
    print(f"{'='*60}")
    counts = Counter(f["severity"] for f in findings)
    for sev in ("critical", "moderate", "minor"):
        print(f"  {sev:<10} {counts.get(sev, 0)}")

    sev_rank = {"critical": 0, "moderate": 1, "minor": 2}
    findings.sort(key=lambda f: sev_rank.get(f["severity"], 3))
    for f in findings:
        print(f"\n  [{f['severity'].upper()}] {f['test']}")
        print(f"    Endpoint:  {f['endpoint']}")
        print(f"    Status:    {f['status']}")
        print(f"    Why:       {f['reasoning']}")
        print(f"    Repro:     {f['reproduction']}")

    if args.output:
        report = {"total_cases": total, "findings": findings, "summary": dict(Counter(f["severity"] for f in findings)), "fuzzed_at": datetime.now().isoformat()}
        if args.output.endswith(".json"):
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
        else:
            with open(args.output, "w") as f:
                f.write(f"# API Fuzz Report\n\nTotal cases: {total}, Findings: {len(findings)}\n\n")
                for x in findings:
                    f.write(f"## [{x['severity'].upper()}] {x['test']}\n\nEndpoint: `{x['endpoint']}`\nStatus: {x['status']}\n\n{x['reasoning']}\n\n```\ncurl: {x['reproduction']}\n```\n\n")
        print(f"\nReport saved to {args.output}")

def report(args):
    """Re-render a saved results file."""
    with open(args.results) as f:
        data = json.load(f)
    findings = data.get("findings", data if isinstance(data, list) else [])
    _fuzz_report(findings, data.get("total_cases", len(findings)), args)
    return findings

def _parse_json_array(raw):
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(raw[start:end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []

def main():
    import argparse
    p = argparse.ArgumentParser(prog="api-fuzzer", description="AI-powered API fuzzer")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate adversarial cases (dry run)")
    g.add_argument("--spec", required=True); g.add_argument("--endpoint", default=None)
    g.add_argument("--cases-per-endpoint", type=int, default=8); g.add_argument("--max-endpoints", type=int, default=10)
    g.add_argument("--output", default=None)
    g.set_defaults(fn=generate)

    f = sub.add_parser("fuzz", help="Generate + execute against a live API")
    f.add_argument("--spec", required=True); f.add_argument("--base", required=True)
    f.add_argument("--endpoint", default=None); f.add_argument("--security", action="store_true")
    f.add_argument("--cases-per-endpoint", type=int, default=8); f.add_argument("--max-endpoints", type=int, default=10)
    f.add_argument("--output", default=None)
    f.set_defaults(fn=fuzz)

    r = sub.add_parser("report", help="Re-render a saved results file")
    r.add_argument("--results", required=True); r.add_argument("--format", default="markdown")
    r.add_argument("--output", default=None)
    r.set_defaults(fn=report)

    args = p.parse_args()
    args.fn(args)

if __name__ == '__main__':
    main()
