from asyncio import sleep

from api.arknights_data_request import ArknightsDataRequest, create_request_by_token
from api.arknights_data_analysis import ArknightsDataAnalysis
from api.models import Account, GiftRecord, database_manager
from api.datas import GiftCodeInfo


async def update_all_accounts_data():
    print('update_all_accounts_data start')
    account_n = 0
    account: Account
    for account in await database_manager.execute(Account.select().where(Account.available == True)):
        if analysis := await ArknightsDataAnalysis.get_analysis(account):
            account_n += 1
            await analysis.fetch_data()
    print(f'update_all_accounts_data end, update {account_n} accounts')


async def auto_get_gift():
    gift_code = GiftCodeInfo.get_gift_code()
    if not gift_code:
        return

    account: Account
    for account in await database_manager.execute(Account.select().where(Account.owner.is_null(False) & Account.available == True)):
        if not Account.owner.user_config.is_auto_gift:
            continue

        used_gift_code = [record.code for record in await database_manager.execute(GiftRecord.select().where(GiftRecord.account == account))]
        need_gift_code = [code for code in gift_code if code not in used_gift_code]

        if not need_gift_code:
            continue

        request: ArknightsDataRequest = create_request_by_token(account.token, account.channel)
        try:
            for code in need_gift_code:
                await request.try_get_gift(code)
                await sleep(1)
        except ValueError:
            continue
