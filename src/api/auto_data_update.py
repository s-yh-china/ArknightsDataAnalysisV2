from asyncio import sleep

from src.api.arknights_data_request import ArknightsDataRequest, create_request_by_token
from src.api.arknights_data_analysis import ArknightsDataAnalysis
from src.api.databases import Account, GiftRecord
from src.api.datas import GiftCodeInfo


async def update_all_accounts_data():
    print('update_all_accounts_data start')
    account_n = 0
    account: Account
    for account in await Account.select().where(Account.available == True).aio_execute():
        if analysis := await ArknightsDataAnalysis.get_analysis(account):
            account_n += 1
            await analysis.fetch_data()
    print(f'update_all_accounts_data end, update {account_n} accounts')


async def auto_get_gift():
    gift_code = GiftCodeInfo.get_gift_code()
    if not gift_code:
        return

    account: Account
    for account in await Account.select().where(Account.owner.is_null(False) & Account.available == True).aio_execute():
        if not Account.owner.user_config.is_auto_gift:
            continue

        used_gift_code = [record.code for record in await GiftRecord.select().where(GiftRecord.account == account).aio_execute()]
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