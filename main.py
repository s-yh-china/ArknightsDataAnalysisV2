from backapi import users, captcha, accounts, account_datas, statistics, email
from api.datas import ConfigData
from api.arknights_data_analysis import ArknightsDataAnalysis
from api.models import Account, database_manager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

config = ConfigData().get_data()

app = FastAPI()

app.include_router(users.router)
app.include_router(captcha.router)
app.include_router(accounts.router)
app.include_router(account_datas.router)
app.include_router(statistics.router)
app.include_router(email.router)

if config['safe']['DEBUG']:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.mount("/test", StaticFiles(directory="test"), name="test")
else:
    app.add_middleware(
        CORSMiddleware,
        **config['safe']['CORS']
    )


@app.get("/")
async def root():
    return {"message": "这里应该放一个系统可用性表"}


async def update_all_accounts_data():
    account: Account
    for account in await database_manager.execute(Account.select()):
        analysis: ArknightsDataAnalysis = await ArknightsDataAnalysis.get_analysis(account)
        if analysis:
            await analysis.fetch_data()


@app.on_event("startup")
async def startup_event():
    scheduler = AsyncIOScheduler()
    minute, hour, day, month, day_of_week = config['analysis']['update_time'].split()
    scheduler.add_job(update_all_accounts_data, 'cron', hour=hour, minute=minute, day=day, month=month, day_of_week=day_of_week)
    scheduler.start()
