from aiogram import Router
from app.handlers.user import start, download, menu, premium, library, feedback, favorites, gate
from app.handlers.admin import setup_admin_routers

def setup_routers() -> Router:
    router = Router()
    router.include_router(setup_admin_routers())
    router.include_router(start.router)
    router.include_router(gate.router)
    router.include_router(download.router)
    router.include_router(menu.router)
    router.include_router(premium.router)
    router.include_router(library.router)
    router.include_router(favorites.router)
    router.include_router(feedback.router)
    return router
