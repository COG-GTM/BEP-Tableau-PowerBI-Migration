import os
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer
import app.main as main_module
import app.queries as queries
import scripts.load_postgres as loader
from scripts.live_feed import fill_staffing_request
from scripts.load_postgres import connect_supabase
from scripts.sign_identity import sign_identity
from app.main import COOKIE_NAME, COOKIE_MAX_AGE, app, serializer

pytestmark = pytest.mark.skipif(
    not os.environ.get("APP_DEMO_PASSWORD") or not os.environ.get("SESSION_SECRET"),
    reason="configure alternate-dashboard environment",
)

def signed_in(email):
    client = TestClient(app)
    response = client.post(
        "/login",
        content=urlencode({"email": email, "password": os.environ["APP_DEMO_PASSWORD"]}),
        headers={"content-type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return client


def test_login_logout_and_idle_timeout():
    client = signed_in("defense.lead@gdit-demo.example")
    assert client.get("/").status_code == 200
    assert client.post("/logout", follow_redirects=False).status_code == 303
    assert client.get("/api/dashboard", follow_redirects=False).status_code == 302
    old = serializer.dumps(
        {
            "email": "exec@gdit-demo.example",
            "last_seen": int(time.time()) - COOKIE_MAX_AGE - 1,
        }
    )
    client.cookies.set(COOKIE_NAME, old)
    assert client.get("/api/dashboard", follow_redirects=False).status_code == 302


def test_failed_login_is_html_401_and_csrf_rejects_foreign_hosts():
    client = TestClient(app)
    failed = client.post(
        "/login",
        content=urlencode({"email": "exec@gdit-demo.example", "password": "wrong"}),
        headers={
            "content-type": "application/x-www-form-urlencoded",
            "origin": "http://testserver",
        },
        follow_redirects=False,
    )
    assert failed.status_code == 401
    assert failed.headers["content-type"].startswith("text/html")
    assert "Sign-in details were not accepted." in failed.text

    assert client.post(
        "/login",
        content=urlencode({"email": "exec@gdit-demo.example", "password": "wrong"}),
        headers={"origin": "https://attacker.example"},
        follow_redirects=False,
    ).status_code == 403
    authenticated = signed_in("defense.lead@gdit-demo.example")
    assert authenticated.post("/logout", headers={"origin": "https://attacker.example"}).status_code == 403
    assert authenticated.post(
        "/api/question",
        json={"template": "attrition_current_scope"},
        headers={"referer": "https://attacker.example/path"},
    ).status_code == 403


def test_app_refuses_missing_or_short_startup_secrets():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("SESSION_SECRET", None)
    env.pop("APP_DEMO_PASSWORD", None)
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "SESSION_SECRET" in result.stderr

    env["SESSION_SECRET"] = "x" * 31
    env["APP_DEMO_PASSWORD"] = "configured"
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "at least 32 characters" in result.stderr

    env["SESSION_SECRET"] = "x" * 32
    env.pop("APP_DEMO_PASSWORD")
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "APP_DEMO_PASSWORD" in result.stderr


def test_signing_key_reuse_rotation_and_cache_fallback(tmp_path, monkeypatch):
    class FakeCursor:
        def __init__(self, key, table_exists):
            self.key = key
            self.table_exists = table_exists
            self.statement = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def execute(self, statement):
            self.statement = statement

        def fetchone(self):
            if "to_regclass" in self.statement:
                return ("security.app_signing_key",) if self.table_exists else (None,)
            return (self.key,) if self.key is not None else None

    class FakeConnection:
        def __init__(self, key=None, table_exists=True):
            self.key = key
            self.table_exists = table_exists

        def cursor(self):
            return FakeCursor(self.key, self.table_exists)

    cache = tmp_path / "app_signing_key"
    monkeypatch.setattr(loader, "SIGNING_KEY_FILE", cache)
    database_key = bytes(range(32))
    cache.write_text(("cached".encode().hex()), encoding="ascii")
    assert loader.read_signing_key(FakeConnection(database_key), rotate=False) == database_key
    rotated = loader.read_signing_key(FakeConnection(database_key), rotate=True)
    assert len(rotated) == 32 and rotated != database_key
    cache_key = bytes(reversed(range(32)))
    cache.write_text(cache_key.hex(), encoding="ascii")
    assert loader.read_signing_key(FakeConnection(table_exists=False), rotate=False) == cache_key


def test_rls_separates_divisions_and_exec_sees_all():
    defense = signed_in("defense.lead@gdit-demo.example").get("/api/dashboard").json()
    intel = signed_in("intel.lead@gdit-demo.example").get("/api/dashboard").json()
    exec_data = signed_in("exec@gdit-demo.example").get("/api/dashboard").json()
    assert defense["visible_divisions"] == ["Defense"]
    assert intel["visible_divisions"] == ["Intelligence"]
    assert set(defense["visible_divisions"]).isdisjoint(intel["visible_divisions"])
    defense_count = sum(row["headcount"] for row in defense["kpis_by_division"])
    intel_count = sum(row["headcount"] for row in intel["kpis_by_division"])
    assert defense_count > 0 and intel_count > 0 and defense_count != intel_count
    assert set(exec_data["visible_divisions"]) == {"Defense", "Intelligence", "Civilian", "Health"}
    assert signed_in("defense.lead@gdit-demo.example").get(
        "/api/dashboard?window_months=12"
    ).json()["window_months"] == 12
    assert signed_in("defense.lead@gdit-demo.example").get(
        "/api/dashboard?window_months=13"
    ).status_code == 400


def test_forged_cookie_is_rejected():
    client = TestClient(app)
    forged = URLSafeTimedSerializer("not-the-session-secret", salt="gdit-alt-dashboard").dumps(
        {"email": "exec@gdit-demo.example", "last_seen": int(time.time())}
    )
    client.cookies.set(COOKIE_NAME, forged)
    assert client.get("/api/dashboard", follow_redirects=False).status_code == 302


def test_governed_question_returns_chart_sql_and_audited_identity():
    client = signed_in("defense.lead@gdit-demo.example")
    result = client.post("/api/question", json={"template": "attrition_current_scope"}).json()
    assert result["answer"] and result["chart"]
    assert result["sql"] == {
        "by_division": queries.GOVERNED_BY_DIVISION_SQL,
        "title_drivers": queries.GOVERNED_TITLE_DRIVERS_SQL,
    }
    expected = json.loads(
        (Path.home() / "gdit/evidence/expected_values_latest.json").read_text()
    )["view_as"]["defense.lead@gdit-demo.example"]["kpis_by_division"][0]
    assert result["by_division"] == [{
        "division": "Defense",
        "latest": expected["vol_exits_latest"],
        "prior": expected["vol_exits_prior"],
    }]
    connection = connect_supabase("app_reader")
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.user_token', %s, true)",
                    (sign_identity("defense.lead@gdit-demo.example", ttl=300),),
                )
                cursor.execute(
                    "SELECT user_email FROM security.app_audit "
                    "WHERE route = 'attrition_current_scope' ORDER BY ts DESC LIMIT 1"
                )
                assert cursor.fetchone()[0] == "defense.lead@gdit-demo.example"
    finally:
        connection.close()


def test_pages_render_and_refresh():
    client = signed_in("defense.lead@gdit-demo.example")
    for path in ("/", "/staffing-risk", "/training-compliance", "/headcount-budget"):
        assert client.get(path).status_code == 200
    before = client.get("/api/dashboard").json()["freshness"]["event_count"]
    assert before >= 0


def test_governed_question_is_defense_scoped_and_neutral_for_intel():
    exec_result = signed_in("exec@gdit-demo.example").post(
        "/api/question", json={"template": "attrition_current_scope"}
    ).json()
    assert exec_result["by_division"] == [
        {"division": "Defense", "latest": 156, "prior": 78}
    ]
    assert exec_result["title_drivers"]
    assert all("Defense" == row["division"] for row in exec_result["by_division"])
    assert "division = %s" in exec_result["sql"]["by_division"]
    assert "division = %s" in exec_result["sql"]["title_drivers"]

    intel_result = signed_in("intel.lead@gdit-demo.example").post(
        "/api/question", json={"template": "attrition_current_scope"}
    ).json()
    assert intel_result["by_division"] == []
    assert intel_result["title_drivers"] == []
    assert intel_result["answer"] == "No visible rows for Defense."


def test_governed_query_keeps_prior_only_rows_and_executes_returned_sql(monkeypatch):
    executed = []
    results = [
        [{"division": "Defense", "latest": 0, "prior": 4}],
        [],
    ]

    def fake_fetch(_connection, statement, params):
        executed.append((statement, params))
        return results.pop(0)

    monkeypatch.setattr(queries, "fetch", fake_fetch)
    result = queries.defense_attrition_question(None, division="Defense")
    assert result["by_division"] == [
        {"division": "Defense", "latest": 0, "prior": 4}
    ]
    assert executed == [
        (result["sql"]["by_division"], ("Defense",)),
        (result["sql"]["title_drivers"], ("Defense",)),
    ]
    assert result["sql"]["by_division"].count("count(*) FILTER") == 2
    assert "GROUP BY w.division" in result["sql"]["by_division"]


def test_identity_key_mismatch_returns_503(monkeypatch):
    client = signed_in("defense.lead@gdit-demo.example")
    monkeypatch.setattr(main_module, "sign_identity", lambda *_args, **_kwargs: "invalid-token")
    response = client.get("/api/dashboard")
    assert response.status_code == 503
    assert response.json()["error"] == "identity signing key mismatch"


def test_percentage_api_values_are_fractions():
    data = signed_in("exec@gdit-demo.example").get("/api/dashboard").json()
    security = next(
        row
        for row in data["overdue_rate_by_business_unit"]
        if row["business_unit"] == "Intelligence Programs"
    )
    assert security["overdue_rate"] == pytest.approx(0.294, abs=0.001)
    civilian = next(
        row
        for row in data["headcount_vs_budget_at_quarter_end"]
        if row["division"] == "Civilian"
    )
    assert civilian["variance_percent"] == pytest.approx(-0.059, abs=0.002)


def test_multi_seat_staffing_fill_splits_one_seat_and_rolls_back():
    connection = connect_supabase("postgres")

    class RollbackProbe(Exception):
        pass

    try:
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT r.req_id, r.headcount, r.opp_id, r.job_family,
                               r.clearance_required, r.needed_by
                        FROM salesforce.staffing_requests AS r
                        WHERE r.status = 'Open' AND r.headcount > 1
                          AND EXISTS (
                            SELECT 1 FROM workday.workers AS w
                            WHERE w.division = r.division
                              AND w.job_family = r.job_family
                              AND w.hire_date <= current_date
                              AND (w.term_date IS NULL OR w.term_date > current_date)
                              AND CASE w.clearance_level
                                    WHEN 'None' THEN 0 WHEN 'Public Trust' THEN 1
                                    WHEN 'Secret' THEN 2 WHEN 'TS' THEN 3
                                    WHEN 'TS/SCI' THEN 4 ELSE -1 END
                                  >= CASE r.clearance_required
                                    WHEN 'None' THEN 0 WHEN 'Public Trust' THEN 1
                                    WHEN 'Secret' THEN 2 WHEN 'TS' THEN 3
                                    WHEN 'TS/SCI' THEN 4 ELSE 99 END
                          )
                        ORDER BY r.req_id LIMIT 1
                        FOR UPDATE OF r
                        """
                    )
                    original = cursor.fetchone()
                    assert original is not None
                    req_id, headcount, opp_id, job_family, clearance_required, needed_by = original
                    cursor.execute(
                        "SELECT sum(headcount) FROM salesforce.staffing_requests WHERE opp_id = %s",
                        (opp_id,),
                    )
                    requested_before = cursor.fetchone()[0]
                    message = fill_staffing_request(cursor, req_id)
                    assert message and "(split " in message
                    filled_req_id = message.split("(split ", 1)[1].rstrip(")")
                    cursor.execute(
                        "SELECT headcount FROM salesforce.staffing_requests WHERE req_id = %s",
                        (req_id,),
                    )
                    assert cursor.fetchone()[0] == headcount - 1
                    cursor.execute(
                        "SELECT opp_id, job_family, clearance_required, headcount, status, "
                        "filled_date, filled_worker_id, needed_by FROM salesforce.staffing_requests "
                        "WHERE req_id = %s",
                        (filled_req_id,),
                    )
                    filled = cursor.fetchone()
                    assert (
                        filled[0] == opp_id
                        and filled[1] == job_family
                        and filled[2] == clearance_required
                        and filled[3] == 1
                        and filled[4] == "Filled"
                        and filled[7] == needed_by
                    )
                    assert filled[5] is not None and filled[6] is not None
                    cursor.execute(
                        "SELECT sum(headcount) FROM salesforce.staffing_requests WHERE opp_id = %s",
                        (opp_id,),
                    )
                    assert cursor.fetchone()[0] == requested_before
                    raise RollbackProbe
        except RollbackProbe:
            pass
    finally:
        connection.close()


def test_sql_does_not_filter_division():
    import inspect

    assert "division =" not in inspect.getsource(queries.query_dashboard).lower()


def test_charts_use_vendored_vega_assets():
    template = Path(__file__).parents[1] / "app" / "templates" / "page.html"
    content = template.read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net/npm/vega" not in content
    for asset in ("vega.min.js", "vega-lite.min.js", "vega-embed.min.js"):
        assert (template.parents[1] / "static" / "vendor" / asset).is_file()
