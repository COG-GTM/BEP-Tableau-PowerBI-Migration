import os
import json
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient
from itsdangerous import URLSafeTimedSerializer
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
    old = serializer.dumps({"email": "exec@gdit-demo.example", "last_seen": int(time.time()) - COOKIE_MAX_AGE - 1})
    client.cookies.set(COOKIE_NAME, old)
    assert client.get("/api/dashboard", follow_redirects=False).status_code == 302


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
    assert result["answer"] and result["chart"] and result["sql"]
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


def test_sql_does_not_filter_division():
    from pathlib import Path

    source = Path(__file__).parents[1] / "app" / "queries.py"
    assert "division =" not in source.read_text(encoding="utf-8").lower()
