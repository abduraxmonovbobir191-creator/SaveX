from aiogram import Router
from app.handlers.admin import panel, channels, prices, orders

def setup_admin_routers() -> Router:
    router = Router()
    router.include_router(panel.router)
    router.include_router(channels.router)
    router.include_router(prices.router)
    router.include_router(orders.router)
    return router
