from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.backapi import users, captcha
from src.backapi import statistics, email, accounts, account_datas, utils
from src.api.datas import ConfigData
from src.api.auto_data_update import update_all_accounts_data, auto_get_gift

config = ConfigData.get_data()


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa
    scheduler = AsyncIOScheduler()
    minute, hour, day, month, day_of_week = config['analysis']['update_time'].split()
    scheduler.add_job(update_all_accounts_data, 'cron', hour=hour, minute=minute, day=day, month=month, day_of_week=day_of_week, misfire_grace_time=3600)
    minute, hour, day, month, day_of_week = config['analysis']['auto_gift'].split()
    scheduler.add_job(auto_get_gift, 'cron', hour=hour, minute=minute, day=day, month=month, day_of_week=day_of_week, misfire_grace_time=3600)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(captcha.router)
app.include_router(accounts.router)
app.include_router(account_datas.router)
app.include_router(statistics.router)
app.include_router(email.router)
app.include_router(utils.router)

if config['safe']['DEBUG']:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.mount("/test", StaticFiles(directory="test_html"), name="test")
else:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        **config['safe']['CORS']
    )


@app.get("/")
async def root():
    return {"message": "这里应该放一个系统可用性表"}