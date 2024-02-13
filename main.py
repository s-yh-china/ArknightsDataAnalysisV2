from api.datas import ConfigData
from backapi import users, captcha, accounts
from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles

config = ConfigData().get_data().get('safe')

app = FastAPI()

app.include_router(users.router)
app.include_router(captcha.router)
app.include_router(accounts.router)

if config['DEBUG']:
    app.mount("/test", StaticFiles(directory="test"), name="test")


@app.get("/")
async def root():
    return {"message": "这里应该放一个系统可用性表"}
