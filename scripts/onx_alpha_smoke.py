#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def _rand_suffix(length: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


class ApiClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, method=method.upper(), data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                if not body:
                    return {}
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} failed: HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"{method} {path} failed: {exc}") from exc


def ensure_ingress_nodes(client: ApiClient, min_count: int = 2) -> list[dict]:
    nodes = client.request("GET", "/nodes")
    eligible = [
        node
        for node in nodes
        if node.get("role") in {"gateway", "mixed"} and node.get("status") != "offline"
    ]
    created: list[dict] = []
    while len(eligible) < min_count:
        suffix = _rand_suffix()
        payload = {
            "name": f"smoke-ingress-{suffix}",
            "role": "gateway",
            "management_address": f"198.51.100.{random.randint(10, 200)}:51820",
            "ssh_host": f"198.51.100.{random.randint(10, 200)}",
            "ssh_port": 22,
            "ssh_user": "root",
            "auth_type": "password",
        }
        node = client.request("POST", "/nodes", payload)
        node = client.request("PATCH", f"/nodes/{node['id']}", {"status": "reachable"})
        eligible.append(node)
        created.append(node)
    return eligible[:min_count]


def main() -> int:
    parser = argparse.ArgumentParser(description="ONX Alpha smoke test for client ingress protocol")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8081/api/v1",
        help="Base ONX API URL (default: http://127.0.0.1:8081/api/v1)",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    client = ApiClient(args.base_url, timeout=args.timeout)

    try:
        health = client.request("GET", "/health")
        if health.get("status") != "ok":
            raise RuntimeError("Health endpoint did not return status=ok")

        nodes = ensure_ingress_nodes(client, min_count=2)
        print(f"[smoke] ingress candidates available: {len(nodes)}")

        bootstrap = client.request(
            "POST",
            "/bootstrap",
            {
                "device_id": f"smoke-device-{_rand_suffix()}",
                "client_public_ip": "203.0.113.50",
                "client_country_code": "RU",
                "destination_country_code": "US",
                "candidate_limit": 4,
                "metadata": {"source": "alpha-smoke"},
            },
        )
        session_id = bootstrap["session_id"]
        session_token = bootstrap["session_token"]
        probe_targets = bootstrap.get("probe_targets", [])
        if not probe_targets:
            raise RuntimeError("Bootstrap returned empty probe_targets")

        measurements: list[dict] = []
        for i, item in enumerate(probe_targets[:2]):
            measurements.append(
                {
                    "node_id": item["node_id"],
                    "rtt_ms": 30.0 + i * 12.0,
                    "jitter_ms": 2.5 + i * 1.2,
                    "loss_pct": 0.1 + i * 0.4,
                    "handshake_ms": 18.0 + i * 8.0,
                    "throughput_mbps": 160.0 - i * 20.0,
                    "raw": {
                        "sample_ts": datetime.now(timezone.utc).isoformat(),
                        "probe_seq": i + 1,
                    },
                }
            )

        probe_result = client.request(
            "POST",
            "/probe",
            {
                "session_id": session_id,
                "session_token": session_token,
                "measurements": measurements,
            },
        )
        if probe_result.get("accepted", 0) < 1:
            raise RuntimeError("Probe report did not accept any measurements")

        decision = client.request(
            "POST",
            "/best-ingress",
            {
                "session_id": session_id,
                "session_token": session_token,
                "require_fresh_probe": True,
                "max_candidates": 3,
            },
        )
        selected = decision.get("selected", {})
        if not selected.get("node_id"):
            raise RuntimeError("best-ingress response has no selected node_id")

        rebind = client.request(
            "POST",
            "/session-rebind",
            {
                "session_id": session_id,
                "session_token": session_token,
                "force": True,
            },
        )
        if not rebind.get("current_node_id"):
            raise RuntimeError("session-rebind response has no current_node_id")

        print("[smoke] OK")
        print(f"[smoke] selected ingress: {selected.get('node_name')} ({selected.get('node_id')})")
        print(f"[smoke] rebind reason: {rebind.get('reason')}")
        return 0
    except Exception as exc:
        print(f"[smoke] FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
