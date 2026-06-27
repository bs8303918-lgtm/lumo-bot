from aiogram import Router

from bot.handlers import admin, admin_interest, callbacks, campaign_callbacks, channels, interests, menu, start, support, test, webapp

router = Router()
router.include_router(start.router)
router.include_router(webapp.router)
router.include_router(menu.router)
router.include_router(support.router)
router.include_router(channels.router)
router.include_router(interests.router)
router.include_router(test.router)
router.include_router(callbacks.router)
router.include_router(campaign_callbacks.router)
router.include_router(admin.router)
router.include_router(admin_interest.router)
