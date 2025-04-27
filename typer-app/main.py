from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from decouple import config
from fastapi import FastAPI, Request, Form, Cookie, Depends
from fastapi.responses import FileResponse, RedirectResponse
from dbase import (
    user_create,
    user_find,
    user_stats_update,
    user_stats_get,
    top_users_get,
)
import jwt
import time
import yaml
import random
import re

app = FastAPI()
templates = Jinja2Templates(directory="static/html")
app.mount("/static", StaticFiles(directory="static"))
JWT_SECRET = config("secret")
JWT_ALGORITHM = config("algorithm")
PASSWORD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
VALID_PASSWORD = re.compile(r"[a-zA-Z0-9!@#\$%\^&\*\(\)_\+.,]{8,30}")

with open("questions.yaml", "r") as f:
    try:
        answers = yaml.safe_load(f)
        questions = [i for i in answers]
        questions_amount = len(questions)
    except Exception as e:
        print(e)


def validate(username: str, password: str) -> [str]:
    errors = []
    if not username:
        return ["Username is empty!"]
    elif len(username) < 5:
        errors.append("Username should be longer then 5 symbols!")
    elif len(username) > 20:
        errors.append("Username should be shorter then 20 symbols!")
    elif not username.isalnum():
        errors.append("Username should contain only letters and numbers")
    if not password:
        return ["Password is empty!"]
    elif len(password) < 8:
        errors.append("Password should be longer then 8 symbols!")
    elif not VALID_PASSWORD.match(password):
        errors.append(
            'Username should contain only letters, numbers and "!@#$%^&*()_+.," symbols'
        )
    return errors


def make_jwt(nickname: str) -> str:
    return jwt.encode(
        {
            "username": nickname,
            "exp": time.time() + 3600,
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def get_username_from_token(token: str = Cookie(default=None)) -> str | None:
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return (
            decoded_token["username"] if decoded_token["exp"] >= time.time() else None
        )
    except:
        return None


@app.get("/")
async def start():
    return FileResponse("static/html/start.html")


@app.get("/login")
async def login(request: Request, auth_username=Depends(get_username_from_token)):
    if auth_username:
        return RedirectResponse("/user", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "feedback": ""}
    )


@app.post("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("token")
    return response


@app.get("/register")
async def register(request: Request):
    return templates.TemplateResponse(
        "register.html", {"request": request, "feedback": ""}
    )


@app.post("/user-login")
async def user_login(request: Request, username: str = Form(), password: str = Form()):
    user = await user_find(username)
    if not user:
        return templates.TemplateResponse(
            "register.html", {"request": request, "feedback": "User does not exist!"}
        )
    if PASSWORD_CONTEXT.verify(password, user["password"]):
        response = RedirectResponse("/user", status_code=302)
        response.set_cookie("token", make_jwt(username))
        return response
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "feedback": "Incorrect password or username!"},
    )


@app.post("/user-register")
async def user_register(
    request: Request, username: str = Form(), password: str = Form()
):
    result = await user_find(username)
    if result:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "errors": ["User is already registered!"]},
        )
    errors = validate(username, password)
    if errors:
        return templates.TemplateResponse(
            "register.html", {"request": request, "errors": errors}
        )
    result = await user_create(username, PASSWORD_CONTEXT.hash(password))
    if not result:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "errors": ["You are successfully registered!"]},
        )
    return templates.TemplateResponse(
        "login.html", {"request": request, "errors": ["Sorry, try again"]}
    )


@app.post("/type", tags=["authentificated"])
async def type(
    request: Request,
    question: str = Form(default=None),
    answer: str = Form(default=None),
    start_time: str = Form(default=None),
    auth_username: str = Depends(get_username_from_token),
):
    if not auth_username:
        return RedirectResponse("/login", status_code=302)
    if start_time:
        right_answer: bool = answer == answers[question]
        stats = await user_stats_get(auth_username)
        if not stats:
            return RedirectResponse("/login", status_code=302)
        await user_stats_update(
            auth_username,
            [
                stats[0] + right_answer,
                stats[1] + int(not right_answer and bool(answer)),
                stats[2] + int(not answer),
            ],
        )
        return templates.TemplateResponse(
            "type.html",
            {
                "request": request,
                "question": questions[random.randrange(questions_amount)],
                "res": "skip" if not answer else "true" if right_answer else "false",
                "feedback": f"Time elapsed: {str(round(time.time() - float(start_time), 3))} seconds"
                if right_answer
                else f"Answer was: {answers[question]}",
                "start_time": str(round(time.time(), 3)),
            },
        )
    else:
        return templates.TemplateResponse(
            "first_type.html",
            {
                "request": request,
                "question": questions[random.randrange(questions_amount)],
                "start_time": str(round(time.time())),
            },
        )


@app.get("/user", tags=["authentificated"])
async def get_stats(
    request: Request, auth_username: str = Depends(get_username_from_token)
):
    if not auth_username:
        return RedirectResponse("/login", status_code=302)
    user_stats = await user_stats_get(auth_username)
    if user_stats:
        return templates.TemplateResponse(
            "user.html",
            {"request": request, "username": auth_username, "stats": user_stats},
        )
    return templates.TemplateResponse(
        "login.html", {"request": request, "feedback": "Sorry, try again"}
    )


@app.get("/top")
async def get_top(request: Request):
    top_users = await top_users_get()
    return templates.TemplateResponse(
        "top.html",
        {"request": request, "top_users": top_users, "top_size": len(top_users)},
    )
