from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config import conf
from src.api.auto_data_update import update_all_accounts_data, auto_get_gift, update_pool_info
from src.backapi import users, captcha
from src.backapi import statistics, email, accounts, account_datas, utils


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa
    scheduler = AsyncIOScheduler()

    scheduler.add_job(update_all_accounts_data, CronTrigger.from_crontab(conf.analysis.update_time), misfire_grace_time=3)
    scheduler.add_job(auto_get_gift, CronTrigger.from_crontab(conf.analysis.auto_gift), misfire_grace_time=3600)
    scheduler.add_job(update_pool_info, CronTrigger.from_crontab(conf.analysis.pool_info_update), misfire_grace_time=60)

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

if conf.safe.DEBUG:
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
        **conf.safe.CORS.model_dump()
    )


@app.get("/")
async def root():
    return {"status": "ok"}
