#!/usr/bin/env python3
"""api-fuzzer CLI entrypoint delegating to backend domain services."""
import argparse
import asyncio
import json
import os
import sys
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_server(args):
    """Launch FastAPI application server."""
    from backend.app.core.config import get_settings
    settings = get_settings()
    uvicorn.run("backend.app.main:app", host=args.host or settings.host, port=args.port or settings.port, reload=args.reload)


def run_generate(args):
    """Generate adversarial test cases from OpenAPI specification."""
    from backend.app.services.spec_parser import parse_spec_full
    from backend.app.services.mutation_engine import MutationEngine
    with open(args.spec) as f:
        content = f.read()
    _, endpoints = parse_spec_full(content)
    if args.endpoint:
        endpoints = [e for e in endpoints if args.endpoint in e.path]
    engine = MutationEngine()
    cases = []
    for ep in endpoints[:args.max_endpoints]:
        cases.extend([c.model_dump() for c in engine.build_cases(ep, cases_per_endpoint=args.cases_per_endpoint)])
    print(f"Generated {len(cases)} adversarial test cases.")
    if args.output:
        with open(args.output, "w") as f:
            json.dump(cases, f, indent=2)


def run_benchmark(args):
    """Execute AI/ML evaluation benchmark."""
    from backend.app.services.evaluation import run_evaluation_benchmark
    res = run_evaluation_benchmark()
    print(json.dumps(res, indent=2))


def main():
    p = argparse.ArgumentParser(prog="api-fuzzer", description="AI-powered OpenAPI adversarial fuzzer")
    sub = p.add_subparsers(dest="cmd")

    srv = sub.add_parser("serve", help="Run FastAPI API and UI backend server")
    srv.add_argument("--host", default=None); srv.add_argument("--port", type=int, default=None); srv.add_argument("--reload", action="store_true")
    srv.set_defaults(fn=run_server)

    gen = sub.add_parser("generate", help="Generate adversarial test cases (dry run)")
    gen.add_argument("--spec", required=True); gen.add_argument("--endpoint", default=None)
    gen.add_argument("--cases-per-endpoint", type=int, default=6); gen.add_argument("--max-endpoints", type=int, default=10)
    gen.add_argument("--output", default=None)
    gen.set_defaults(fn=run_generate)

    bench = sub.add_parser("benchmark", help="Run AI/ML evaluation benchmark")
    bench.set_defaults(fn=run_benchmark)

    args = p.parse_args()
    if not args.cmd:
        run_server(args)
    else:
        args.fn(args)


if __name__ == "__main__":
    main()
