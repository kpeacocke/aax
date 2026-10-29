#!/usr/bin/env python3
"""Exercise the real EDA HTTP API, dispatcher, decision image and log callback."""

import argparse
import base64
from contextlib import contextmanager
import http.cookiejar
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


class APIRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self, base_url: str):
        self.base_url = base_url

    def redirect_request(self, request, response, code, message, headers, new_url):
        if not new_url.startswith(self.base_url):
            raise ValueError("Refusing to redirect credentials outside the EDA API")
        return super().redirect_request(request, response, code, message, headers, new_url)


class API:
    def __init__(self, base_url: str, authorization: str = "", session_id: str = ""):
        self.base_url = base_url.rstrip("/") + "/"
        self.authorization = authorization
        self.session_id = session_id
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies),
            APIRedirectHandler(self.base_url),
        )

    def request(self, method: str, path: str, data=None, authenticated: bool = True):
        url = urllib.parse.urljoin(self.base_url, path)
        if not url.startswith(self.base_url):
            raise ValueError("Refusing to send credentials outside the EDA API")
        headers = {"Accept": "application/json"}
        if authenticated:
            if self.authorization:
                headers["Authorization"] = self.authorization
            if self.session_id:
                headers["Cookie"] = "sessionid=" + self.session_id
                csrf = next((c.value for c in self.cookies if c.name == "csrftoken"), "")
                if csrf:
                    headers["Cookie"] += "; csrftoken=" + csrf
                    headers["X-CSRFToken"] = csrf
        body = None if data is None else json.dumps(data).encode()
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        opener = self.opener if authenticated else urllib.request.build_opener()
        try:
            with opener.open(request, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            # Do not log request/response bodies: credential endpoints contain secrets.
            raise RuntimeError(f"EDA {method} {path}: HTTP {error.code}") from None

    def results(self, path: str) -> list:
        results = []
        while path:
            page = self.request("GET", path)
            results.extend(page["results"])
            path = page["next"]
        return results

    def ensure(self, path: str, payload: dict) -> dict:
        matches = [r for r in self.results(path) if r["name"] == payload["name"]]
        if len(matches) > 1:
            raise RuntimeError(f"Duplicate acceptance resource at {path}")
        if matches:
            return self.request("GET", f"{path}{matches[0]['id']}/")
        return self.request("POST", path, payload)


@contextmanager
def authentication(local_user: str, base_url: str):
    session = None
    try:
        if local_user:
            if urllib.parse.urlparse(base_url).hostname not in ("127.0.0.1", "localhost"):
                raise ValueError("--local-user is restricted to the controller loopback API")
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aap_eda.settings.default")
            import django

            django.setup()
            from django.contrib.auth import (
                BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model,
            )
            from django.contrib.sessions.backends.db import SessionStore

            user = get_user_model().objects.get(username=local_user)
            if not user.is_active or not user.is_superuser:
                raise ValueError("--local-user requires an existing active administrator")
            session = SessionStore()
            session[SESSION_KEY] = str(user.pk)
            session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
            session[HASH_SESSION_KEY] = user.get_session_auth_hash()
            session.create()
            yield API(base_url, session_id=session.session_key)
        else:
            username = os.environ["EDA_TEST_USERNAME"]
            password = os.environ["EDA_TEST_PASSWORD"]
            if urllib.parse.urlparse(base_url).scheme != "https":
                raise ValueError("Remote password authentication requires HTTPS")
            encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
            yield API(base_url, authorization="Basic " + encoded)
    finally:
        if session is not None:
            session.delete()


def poll(read, ready, timeout: int, label: str):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = read()
        if ready(last):
            return last
        if str(last.get("status", "")).lower() in ("failed", "error"):
            raise RuntimeError(f"{label} failed; inspect EDA status and instance logs")
        if str(last.get("import_state", "")).lower() in ("failed", "error"):
            raise RuntimeError(f"{label} import failed; inspect project import_error")
        time.sleep(3)
    raise TimeoutError(f"{label} did not pass within {timeout}s; last status: "
                       f"{last.get('status', last.get('import_state')) if last else 'none'}")


def prepare(api: API, args) -> dict:
    project = api.ensure("projects/", {
        "name": args.prefix + "-project", "organization_id": args.organization_id,
        "url": args.git_url, "scm_branch": args.git_ref, "verify_ssl": True,
    })
    if project["url"] != args.git_url or project["scm_branch"] != args.git_ref:
        raise ValueError("Existing acceptance project has a different Git source")
    project = poll(
        lambda: api.request("GET", f"projects/{project['id']}/"),
        lambda p: p["import_state"].lower() == "completed", args.timeout, "Git project",
    )
    decision = api.ensure("decision-environments/", {
        "name": args.prefix + "-decision", "organization_id": args.organization_id,
        "image_url": args.decision_image, "pull_policy": "missing",
    })
    if decision["image_url"] != args.decision_image:
        raise ValueError("Existing acceptance decision environment has a different image")
    rulebooks = api.results(f"rulebooks/?project_id={project['id']}")
    expected = "aax-awx-readiness.yml" if args.phase == "launch" else "aax-debug.yml"
    rulebook = next((r for r in rulebooks if r["name"] == expected), None)
    if rulebook is None:
        raise RuntimeError(f"Git project did not discover {expected}")
    marker = args.prefix + "-event"
    payload = {
        "name": args.prefix + ("-action" if args.phase == "launch" else "-debug"),
        "organization_id": args.organization_id,
        "decision_environment_id": decision["id"], "rulebook_id": rulebook["id"],
        "is_enabled": True, "restart_policy": "always",
        "extra_var": json.dumps({"aax_acceptance_marker": marker,
                                 "awx_organization": args.awx_organization}),
    }
    if args.phase == "launch":
        if args.awx_token_id is None or not args.awx_organization:
            raise ValueError("AWX action requires --awx-token-id and --awx-organization")
        payload["awx_token_id"] = args.awx_token_id
        payload["restart_policy"] = "never"
    activation = api.ensure("activations/", payload)
    if activation["rulebook"]["id"] != rulebook["id"]:
        raise ValueError("Existing acceptance activation has a different rulebook")
    return {
        "activation_id": activation["id"], "project_id": project["id"],
        "decision_environment_id": decision["id"], "rulebook_id": rulebook["id"],
        "git_hash": project["git_hash"], "marker": marker, "last_log_id": 0,
    }


def check(api: API, state: dict, timeout: int) -> dict:
    activation = poll(
        lambda: api.request("GET", f"activations/{state['activation_id']}/"),
        lambda a: a["status"].lower() == "running", timeout, "Activation",
    )
    if not activation["is_enabled"]:
        raise RuntimeError("Acceptance activation is not enabled")
    if activation["git_hash"] != state["git_hash"]:
        raise RuntimeError("Activation is not running the recorded Git revision")
    instances = activation["instances"]
    if not instances:
        raise RuntimeError("Running activation has no instance")
    instance = max(instances, key=lambda i: i["id"])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        logs = api.results(f"activation-instances/{instance['id']}/logs/")
        markers = [log for log in logs if state["marker"] in log["log"]
                   and log["id"] > state["last_log_id"]]
        if markers:
            return {**state, "instance_id": instance["id"], "status": "running",
                    "last_log_id": max(log["id"] for log in markers)}
        time.sleep(3)
    raise TimeoutError("Running activation did not deliver a fresh debug marker to EDA logs")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/api/eda/v1/")
    parser.add_argument("--local-user", default="")
    parser.add_argument("--phase", choices=("prepare", "check", "launch", "disable"), required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--prefix", default="aax-acceptance")
    parser.add_argument("--organization-id", type=int, default=1)
    parser.add_argument("--git-url", default="https://github.com/kpeacocke/aax.git")
    parser.add_argument("--git-ref", default="main")
    parser.add_argument("--decision-image")
    parser.add_argument("--awx-token-id", type=int)
    parser.add_argument("--awx-organization", default="")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", args.prefix):
        parser.error("--prefix must be a short lowercase run-scoped name")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.phase in ("prepare", "launch") and (
        not args.decision_image or "@sha256:" not in args.decision_image
    ):
        parser.error("--decision-image must identify an immutable scanned digest")
    with authentication(args.local_user, args.base_url) as api:
        try:
            api.request("GET", "projects/", authenticated=False)
        except RuntimeError as error:
            if not str(error).endswith("HTTP 401"):
                raise
        else:
            raise RuntimeError("Unauthenticated EDA API unexpectedly accepted access")
        api.request("GET", "auth/session/login/")
        if args.phase in ("prepare", "launch"):
            if args.state_file.exists():
                raise ValueError("State file already exists; use check or a new run prefix")
            state = prepare(api, args)
        else:
            state = json.loads(args.state_file.read_text())
            if args.phase == "check":
                state = check(api, state, args.timeout)
            else:
                api.request("POST", f"activations/{state['activation_id']}/disable/", {})
                state["status"] = "disable-requested"
    args.state_file.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state))


if __name__ == "__main__":
    main()
