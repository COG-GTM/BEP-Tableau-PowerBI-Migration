from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from psycopg.rows import dict_row

from app.queries import DEMO_ROOT, defense_attrition_question, query_dashboard
from scripts.load_postgres import connect_supabase
from scripts.sign_identity import sign_identity

DEMO_PASSWORD = os.environ.get("APP_DEMO_PASSWORD", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
COOKIE_NAME = "gdit_session"
COOKIE_MAX_AGE = 900
COOKIE_SECURE = os.environ.get("APP_COOKIE_SECURE", "1") != "0"
ALLOWED_USERS = {
    "exec@gdit-demo.example",
    "defense.lead@gdit-demo.example",
    "intel.lead@gdit-demo.example",
    "hr.analyst@gdit-demo.example",
}
serializer = URLSafeTimedSerializer(SESSION_SECRET or "missing-session-secret", salt="gdit-alt-dashboard")
templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)
app = FastAPI(title="GDIT Workforce & Pipeline")


def _session(email: str) -> str:
    return serializer.dumps({"email": email, "last_seen": int(time.time())})


@app.middleware("http")
async def session_guard(request: Request, call_next):
    if request.url.path not in {"/login", "/health"}:
        token = request.cookies.get(COOKIE_NAME)
        try:
            payload = serializer.loads(token, max_age=COOKIE_MAX_AGE)
            email = payload["email"]
            if email not in ALLOWED_USERS or int(time.time()) - int(payload["last_seen"]) > COOKIE_MAX_AGE:
                raise BadSignature("expired idle session")
            request.state.email = email
        except (BadSignature, KeyError, TypeError, ValueError):
            return RedirectResponse("/login", status_code=302)
    response = await call_next(request)
    if hasattr(request.state, "email") and request.url.path != "/logout":
        response.set_cookie(
            COOKIE_NAME, _session(request.state.email), max_age=COOKIE_MAX_AGE,
            httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/",
        )
    return response


def _row_count(data: dict) -> int:
    return sum(len(value) for value in data.values() if isinstance(value, list))


def _as_user(email: str, route: str, params: dict, callback):
    if not DEMO_PASSWORD or not SESSION_SECRET:
        raise RuntimeError("APP_DEMO_PASSWORD and SESSION_SECRET must be configured")
    connection = connect_supabase("app_reader")
    try:
        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT set_config('app.user_token', %s, true)",
                    (sign_identity(email, ttl=300, cached_only=True),),
                )
            data = callback(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT security.log_query(%s, %s::jsonb, %s)",
                    (route, json.dumps(params, sort_keys=True), _row_count(data)),
                )
        return data
    finally:
        connection.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return templates.get_template("login.html").render(users=sorted(ALLOWED_USERS))


@app.post("/login")
async def login(request: Request):
    form = parse_qs((await request.body()).decode("utf-8"))
    email = form.get("email", [""])[0].lower()
    password = form.get("password", [""])[0]
    if email not in ALLOWED_USERS or not DEMO_PASSWORD or password != DEMO_PASSWORD:
        return templates.get_template("login.html").render(
            users=sorted(ALLOWED_USERS), error="Sign-in details were not accepted."
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME, _session(email), max_age=COOKIE_MAX_AGE,
        httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/",
    )
    return response


@app.post("/logout")
def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


PAGE_TITLES = {
    "/": "Attrition Watch",
    "/staffing-risk": "Staffing Risk",
    "/training-compliance": "Training Compliance",
    "/headcount-budget": "Headcount vs Budget",
}


@app.get("/", response_class=HTMLResponse)
@app.get("/staffing-risk", response_class=HTMLResponse)
@app.get("/training-compliance", response_class=HTMLResponse)
@app.get("/headcount-budget", response_class=HTMLResponse)
def page(request: Request):
    path = request.url.path
    data = _as_user(request.state.email, path, {}, query_dashboard)
    return templates.get_template("page.html").render(
        email=request.state.email,
        title=PAGE_TITLES[path],
        data=json.dumps(jsonable_encoder(data)),
        divisions=data["visible_divisions"],
    )


@app.get("/api/dashboard")
def dashboard(request: Request):
    try:
        window_months = int(request.query_params.get("window_months", "3"))
    except ValueError:
        return JSONResponse({"error": "window_months must be between 1 and 12"}, status_code=400)
    if not 1 <= window_months <= 12:
        return JSONResponse({"error": "window_months must be between 1 and 12"}, status_code=400)
    account = request.query_params.get("account")
    params = {"window_months": window_months, "account": account}
    data = _as_user(
        request.state.email,
        "api.dashboard",
        params,
        lambda connection: query_dashboard(connection, window_months, account),
    )
    return JSONResponse(jsonable_encoder(data))


@app.post("/api/question")
async def question(request: Request):
    payload = await request.json()
    template = payload.get("template")
    if template != "attrition_current_scope":
        return JSONResponse({"error": "Question template is not available."}, status_code=400)
    result = _as_user(
        request.state.email,
        template,
        {"window_months": 3},
        defense_attrition_question,
    )
    return JSONResponse(jsonable_encoder(result))
