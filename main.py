from api.datas import ConfigData
from backapi import users, captcha, accounts, account_datas
from fastapi import FastAPI

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

config = ConfigData().get_data().get('safe')

app = FastAPI()

app.include_router(users.router)
app.include_router(captcha.router)
app.include_router(accounts.router)
app.include_router(account_datas.router)

if config['DEBUG']:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.mount("/test", StaticFiles(directory="test"), name="test")


@app.get("/")
async def root():
    return {"message": "这里应该放一个系统可用性表"}
