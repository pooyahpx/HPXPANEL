from aiogram import Dispatcher

from . import admin, base, client, error_handler, shop, shop_admin


def include_routers(dp: Dispatcher) -> None:
    dp.include_router(base.router)
    dp.include_router(shop.router)
    dp.include_router(shop_admin.router)
    dp.include_router(admin.router)
    dp.include_router(client.router)
    dp.include_router(error_handler.router)
