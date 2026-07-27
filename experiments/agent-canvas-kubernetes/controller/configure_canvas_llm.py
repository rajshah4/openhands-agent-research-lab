#!/usr/bin/env python3
"""Configure one private Agent Canvas LLM profile without printing secrets."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from research_lab.cli import _load_env_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--profile", default="neurogolf-haiku")
    parser.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5-20251001",
    )
    return parser.parse_args()


def request(
    method: str,
    url: str,
    session_key: str,
    body: dict[str, Any] | None = None,
) -> Any:
    payload = json.dumps(body).encode() if body is not None else None
    headers = {
        "X-Session-API-Key": session_key,
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                url,
                data=payload,
                headers=headers,
                method=method,
            ),
            timeout=60,
        ) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        path = urllib.parse.urlsplit(url).path
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}") from exc
    return json.loads(raw) if raw else None


def main() -> int:
    args = parse_args()
    _load_env_file(args.env_file)
    session_key = os.environ.get("CANVAS_API_KEY", "").strip()
    provider_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not session_key:
        raise SystemExit("CANVAS_API_KEY is required")
    if not provider_key:
        raise SystemExit("ANTHROPIC_API_KEY is required")

    base = args.base_url.rstrip("/")
    profile_url = (
        f"{base}/api/profiles/{urllib.parse.quote(args.profile, safe='')}"
    )
    llm = {
        "model": args.model,
        "api_key": provider_key,
        "extended_thinking_budget": 1024,
        "max_output_tokens": 4096,
        "temperature": 0,
    }
    request(
        "POST",
        profile_url,
        session_key,
        {"llm": llm, "include_secrets": True},
    )
    request("POST", f"{profile_url}/activate", session_key)
    request(
        "PATCH",
        f"{base}/api/settings",
        session_key,
        {
            "agent_settings_diff": {
                "llm": llm,
                "enable_sub_agents": False,
                "tool_concurrency_limit": 1,
            },
            "conversation_settings_diff": {
                "confirmation_mode": False,
                "max_iterations": 50,
            },
        },
    )

    settings = request("GET", f"{base}/api/settings", session_key) or {}
    profiles = request("GET", f"{base}/api/profiles", session_key) or {}
    agent_settings = settings.get("agent_settings") or {}
    result = {
        "profile": args.profile,
        "active_profile": profiles.get("active_profile"),
        "llm_api_key_is_set": bool(settings.get("llm_api_key_is_set")),
        "model": (agent_settings.get("llm") or {}).get("model"),
        "enable_sub_agents": agent_settings.get("enable_sub_agents"),
        "tool_concurrency_limit": agent_settings.get("tool_concurrency_limit"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["active_profile"] != args.profile:
        return 2
    if not result["llm_api_key_is_set"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
