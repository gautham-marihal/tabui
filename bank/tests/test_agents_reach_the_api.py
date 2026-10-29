"""Every request the six banking agents can make (their tools, hooks, task steps and hand-overs) reaches a route of this
API, so nothing fails with a 404 in a call. The agents are built by their generators in Weave Studio
(mock-bank/agents/build.mjs): set WEAVE_AGENTS_DIR to that folder to run these checks; without it they are skipped."""

import json
import os
import re
import subprocess

import pytest
from fastapi.testclient import TestClient

from bank.app import create_app

AGENTS_DIR = os.environ.get("WEAVE_AGENTS_DIR", "")
pytestmark = pytest.mark.skipif(
    not os.path.isfile(os.path.join(AGENTS_DIR, "build.mjs")),
    reason="set WEAVE_AGENTS_DIR to Weave Studio's mock-bank/agents folder to check the agents against this API",
)
BASE = "http://bank.test"
AGENTS = ["sg-business-banking", "sg-vip-desk", "sg-investigations", "sg-sm-survey", "my-business-banking", "my-consumer-banking"]


def build_agents(base_url: str, reference: dict) -> list[dict]:
    """The agents as their generators build them, from this bank's reference (its lines, hours, holidays, fees)."""
    script = (
        "import { buildAll } from './build.mjs'; let s = ''; process.stdin.on('data', (d) => (s += d)).on('end', () =>"
        f" console.log(JSON.stringify(buildAll({json.dumps(base_url)}, JSON.parse(s)))));"
    )
    done = subprocess.run(
        ["node", "--input-type=module", "-e", script], cwd=AGENTS_DIR, input=json.dumps(reference), capture_output=True, encoding="utf-8", check=True
    )
    return json.loads(done.stdout)


def requests_of(config: dict) -> list[tuple[str, str, str]]:
    """Every HTTP request in an agent configuration: (connection, method, path)."""
    found = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        if node.get("type") == "http" and node.get("connection") and node.get("method") and node.get("path"):
            found.append((node["connection"], node["method"], node["path"]))
        if node.get("type") == "http" and node.get("connection") and isinstance(node.get("request"), dict):
            found.append((node["connection"], node["request"]["method"], node["request"]["path"]))
        if node.get("method") == "http_request" and isinstance(node.get("request"), dict):
            request = node["request"]
            found.append((request["connection"], request["method"], request["path"]))
        for value in node.values():
            walk(value)

    walk(config)
    return found


def reaches_every_route(client: TestClient, configs: list[dict], base: str) -> None:
    for config in configs:
        requests = requests_of(config)
        assert requests, config["meta"]["id"]
        for connection, method, path in requests:
            prefix = config["connections"][connection]["base_url"]
            assert prefix.startswith(base), f"{config['meta']['id']}: connection {connection}"
            # every template filled with digits, which every route's parameters accept
            url = prefix[len(base) :] + re.sub(r"\{\{[^}]+\}\}", "501234567001", path)
            response = client.request(method, url, content=None if method == "GET" else b"{}")
            assert response.status_code != 404, f"{config['meta']['id']}: {method} {connection}{path} has no route"


@pytest.fixture
def agents(client):
    return build_agents(BASE, client.get("/hub/reference").json())


def test_the_six_agents_are_built_and_every_request_they_make_has_a_route(client, agents):
    assert [c["meta"]["id"] for c in agents] == AGENTS
    reaches_every_route(client, agents, BASE)


def test_with_a_key_the_api_answers_only_under_it_and_the_agents_built_for_it_still_reach_every_route():
    with TestClient(create_app("k3y")) as keyed:
        for path in ["/", "/activity", "/sg/cmm/promotions", "/wrong/sg/cmm/promotions", "/k3yx/sg/cmm/promotions"]:
            assert keyed.get(path).status_code == 404, path
        assert keyed.get("/k3y").status_code == 200
        assert keyed.get("/k3y/activity").status_code == 200
        assert keyed.get("/k3y/sg/as400/rates/prime").json()["prime_rate_pct"] > 0
        reaches_every_route(keyed, build_agents(f"{BASE}/k3y", keyed.get("/k3y/hub/reference").json()), BASE)
