from __future__ import annotations

import json
import os
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, URLSafeTimedSerializer
from jinja2 import Environment, FileSystemLoader, select_autoescape
import psycopg

from app.queries import (
    DEMO_ROOT,
    GOVERNED_QUESTION_DIVISION,
    defense_attrition_question,
    query_dashboard,
)
from scripts.load_postgres import connect_supabase
from scripts.sign_identity import sign_identity

DEMO_PASSWORD = os.environ.get("APP_DEMO_PASSWORD", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")
if not SESSION_SECRET:
    raise RuntimeError("SESSION_SECRET must be configured")
if len(SESSION_SECRET) < 32:
    raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
if not DEMO_PASSWORD:
    raise RuntimeError("APP_DEMO_PASSWORD must be configured")
COOKIE_NAME = "gdit_session"
COOKIE_MAX_AGE = 900
COOKIE_SECURE = os.environ.get("APP_COOKIE_SECURE", "1") != "0"
ALLOWED_USERS = {
    "exec@gdit-demo.example",
    "defense.lead@gdit-demo.example",
    "intel.lead@gdit-demo.example",
    "hr.analyst@gdit-demo.example",
}
serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="gdit-alt-dashboard")
templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["html"]),
)
app = FastAPI(title="GDIT Workforce & Pipeline")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


class IdentitySigningKeyMismatch(Exception):
    pass


def _session(email: str) -> str:
    return serializer.dumps({"email": email, "last_seen": int(time.time())})


def _csrf_valid(request: Request) -> bool:
    origin = request.headers.get("origin")
    source = origin if origin is not None else request.headers.get("referer")
    if source is None:
        return True
    return urlsplit(source).netloc.casefold() == request.headers.get("host", "").casefold()


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
    connection = connect_supabase("app_reader")
    try:
        try:
            token = sign_identity(email, ttl=300, cached_only=True)
        except RuntimeError as exc:
            raise IdentitySigningKeyMismatch from exc
        try:
            with connection.transaction():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.user_token', %s, true)",
                        (token,),
                    )
                data = callback(connection)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT security.log_query(%s, %s::jsonb, %s)",
                        (route, json.dumps(params, sort_keys=True), _row_count(data)),
                    )
            return data
        except psycopg.Error as exc:
            if exc.sqlstate == "28000":
                raise IdentitySigningKeyMismatch from exc
            raise
    finally:
        connection.close()


@app.exception_handler(IdentitySigningKeyMismatch)
async def identity_signing_key_mismatch(_request: Request, _exc: IdentitySigningKeyMismatch):
    return JSONResponse(
        {"error": "identity signing key mismatch"},
        status_code=503,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return templates.get_template("login.html").render(users=sorted(ALLOWED_USERS))


@app.post("/login")
async def login(request: Request):
    if not _csrf_valid(request):
        return JSONResponse({"error": "Request origin does not match host."}, status_code=403)
    form = parse_qs((await request.body()).decode("utf-8"))
    email = form.get("email", [""])[0].lower()
    password = form.get("password", [""])[0]
    if email not in ALLOWED_USERS or not DEMO_PASSWORD or password != DEMO_PASSWORD:
        return HTMLResponse(
            templates.get_template("login.html").render(
                users=sorted(ALLOWED_USERS), error="Sign-in details were not accepted."
            ),
            status_code=401,
        )
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        COOKIE_NAME, _session(email), max_age=COOKIE_MAX_AGE,
        httponly=True, secure=COOKIE_SECURE, samesite="lax", path="/",
    )
    return response


@app.post("/logout")
def logout(request: Request):
    if not _csrf_valid(request):
        return JSONResponse({"error": "Request origin does not match host."}, status_code=403)
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
    if not _csrf_valid(request):
        return JSONResponse({"error": "Request origin does not match host."}, status_code=403)
    payload = await request.json()
    template = payload.get("template")
    if template != "attrition_current_scope":
        return JSONResponse({"error": "Question template is not available."}, status_code=400)
    params = {"division": GOVERNED_QUESTION_DIVISION, "window_months": 3}
    result = _as_user(
        request.state.email,
        template,
        params,
        lambda connection: defense_attrition_question(
            connection, division=GOVERNED_QUESTION_DIVISION
        ),
    )
    return JSONResponse(jsonable_encoder(result))
