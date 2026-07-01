from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters import AdminFilter
from bot.welcome import send_welcome
from bot.webapp_setup import reset_menu_cache, setup_telegram_webapp, sync_user_menu_button
from db.repositories.channels import ChannelRepository
from db.repositories.opportunity_catalog import OpportunityCatalogRepository
from db.repositories.users import EventRepository, MatchRepository, SystemStateRepository
from db.repositories.users import UserRepository
from config import get_settings
from llm.client import LLMClient
from monitor.telethon_client import telethon_is_authorized
from services.analytics import format_funnel_report
from services.interest_stats import (
    build_interest_overview,
    format_interest_overview,
    format_topic_match,
    search_users_by_topic,
)
from services.maintenance_broadcast import send_maintenance_apology
from services.community_broadcast import get_community_invite_stats, send_community_invite
from services.promo_campaign import (
    format_campaign_message,
    format_campaign_stats_report,
    get_campaign_stats,
    load_campaign,
    run_campaign,
    send_campaign_to_user,
)
from db.repositories.training import TrainingRepository
from services.training_export import export_training_jsonl
from services.subscription_stats import build_subscription_stats, format_subscription_stats_report

router = Router()


@router.message(Command("preview_welcome"), AdminFilter())
async def cmd_preview_welcome(message: Message) -> None:
    """Скрытая команда — превью /start для новых пользователей."""
    await send_welcome(message)


@router.message(Command("health"), AdminFilter())
async def cmd_health(message: Message, session: AsyncSession) -> None:
    state_repo = SystemStateRepository(session)
    channel_repo = ChannelRepository(session)
    event_repo = EventRepository(session)

    last_success = await state_repo.get("last_monitor_success_at", "никогда")
    fail_streak = await state_repo.get("monitor_fail_streak", "0")
    telethon_ok = await telethon_is_authorized()
    llm_ok = await LLMClient().health_check()
    settings = get_settings()
    channels_count = await channel_repo.count_monitored()

    is_admin = settings.is_admin(message.from_user.id)
    admin_line = "да" if is_admin else "нет"
    if settings.telegram_admin_chat_id:
        admin_hint = f"{settings.telegram_admin_chat_id} (ты: {message.from_user.id}, совпадение: {admin_line})"
    else:
        admin_hint = "не задан в .env"

    since = datetime.now(timezone.utc) - timedelta(hours=24)
    errors = await event_repo.count_by_type_since(since)
    error_lines = "\n".join(f"  • {k}: {v}" for k, v in errors.items() if "error" in k or "flood" in k) or "  нет"

    await message.answer(
        f"🏥 Health\n\n"
        f"Mini App URL: {settings.resolved_webapp_url or 'не задан'}\n"
        f"Последний успешный цикл мониторинга: {last_success}\n"
        f"Неудачных циклов подряд: {fail_streak}\n"
        f"Telethon сессия: {'✅ залогинена' if telethon_ok else '❌ не залогинена'}\n"
        f"LLM ({settings.llm_provider}): {'✅ ok' if llm_ok else '❌ недоступен'}\n"
        f"Admin chat ID: {admin_hint}\n"
        f"Каналов в очереди: {channels_count}\n\n"
        f"Ошибки за 24ч:\n{error_lines}"
    )


@router.message(Command("subs"), AdminFilter())
async def cmd_subs(message: Message, session: AsyncSession) -> None:
    """Счётчики подписок: trial, платные, Startify."""
    stats = await build_subscription_stats(session)
    await message.answer(format_subscription_stats_report(stats), parse_mode="HTML")


@router.message(Command("stats"), AdminFilter())
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    match_repo = MatchRepository(session)
    event_repo = EventRepository(session)

    since_7d = datetime.now(timezone.utc) - timedelta(days=7)

    total_users = await user_repo.count_all()
    new_users = await user_repo.count_new_since(since_7d)
    active_users = await event_repo.count_active_users_since(since_7d)
    monitored = await channel_repo.count_monitored()
    avg_channels = await channel_repo.avg_channels_per_user()
    total_cards = await match_repo.count_sent_total()
    cards_7d = await match_repo.count_sent_since(since_7d)

    events_7d = await event_repo.count_by_type_since(since_7d)
    details_clicks = events_7d.get("button_details_click", 0)
    apply_clicks = events_7d.get("button_apply_click", 0)
    sent_7d = events_7d.get("card_sent", 0) or cards_7d or 1
    ctr_details = round(details_clicks / sent_7d * 100, 1)
    ctr_apply = round(apply_clicks / sent_7d * 100, 1)

    top_channels = await match_repo.top_channels_by_matches(5, exclude_seed=True)
    top_text = "\n".join(f"  {i+1}. {name}: {cnt}" for i, (name, cnt) in enumerate(top_channels)) or "  пока нет (только пользовательские каналы)"

    await message.answer(
        f"📊 Stats\n\n"
        f"Всего пользователей: {total_users}\n"
        f"Новых за 7 дней: {new_users}\n"
        f"Активных (матч за 7д): {active_users}\n"
        f"Уникальных каналов: {monitored}\n"
        f"Среднее каналов/пользователь: {avg_channels}\n"
        f"Всего карточек: {total_cards}\n"
        f"Карточек за 7 дней: {cards_7d}\n"
        f"CTR «Подробнее»: {ctr_details}% ({details_clicks}/{sent_7d})\n"
        f"CTR «Подать заявку»: {ctr_apply}% ({apply_clicks}/{sent_7d})\n\n"
        f"Интересы: /interests\n"
        f"Воронка: /funnel\n\n"
        f"Топ-5 каналов по матчам (без seed):\n{top_text}"
    )


@router.message(Command("interests"), AdminFilter())
async def cmd_interests(message: Message, session: AsyncSession) -> None:
    """Сколько пользователей интересуются стартапами, грантами и т.д."""
    user_repo = UserRepository(session)
    total_users = await user_repo.count_all()
    users = await user_repo.list_with_interests()

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1:
        topic = parts[1].strip()
        text = format_topic_match(search_users_by_topic(users, topic, total_users=total_users))
    else:
        overview = build_interest_overview(users, total_users=total_users)
        text = format_interest_overview(overview)

    for chunk in _split_messages(text):
        await message.answer(chunk)


@router.message(Command("funnel"), AdminFilter())
async def cmd_funnel(message: Message, session: AsyncSession) -> None:
    """Воронка онбординга: где пользователи отваливаются."""
    days = 7
    if message.text and len(message.text.split()) >= 2:
        try:
            days = max(1, min(90, int(message.text.split()[1])))
        except ValueError:
            pass

    since = datetime.now(timezone.utc) - timedelta(days=days)
    event_repo = EventRepository(session)
    data = await event_repo.funnel_snapshot(since)
    await message.answer(format_funnel_report(data, days=days))


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message, session: AsyncSession) -> None:
    """Сбросить свой тестовый аккаунт: профиль, каналы, история матчей."""
    user_repo = UserRepository(session)
    channel_repo = ChannelRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("Аккаунт не найден в базе.")
        return
    username = user.username or str(user.telegram_id)
    for uc in await channel_repo.get_user_channels(user.id):
        await channel_repo.purge_channel_feed(uc.channel_identifier)
    await user_repo.delete_user(user.id)
    await session.commit()
    await message.answer(
        f"🗑 Аккаунт @{username} удалён из базы.\n"
        "Его каналы больше не участвуют в рассылке.\n"
        "Напиши /start — зарегистрируешься заново с чистого листа."
    )


@router.message(Command("purge_user"), AdminFilter())
async def cmd_purge_user(message: Message, session: AsyncSession) -> None:
    """Удалить пользователя по @username (только админ)."""
    if not message.text or len(message.text.split()) < 2:
        await message.answer("Использование: /purge_user @username")
        return
    username = message.text.split(maxsplit=1)[1].strip()
    user_repo = UserRepository(session)
    user = await user_repo.find_by_username(username)
    if not user:
        await message.answer(f"Пользователь {username} не найден.")
        return
    await user_repo.delete_user(user.id)
    await session.commit()
    await message.answer(f"🗑 Пользователь @{user.username or user.telegram_id} удалён.")


@router.message(Command("purge_channel"), AdminFilter())
async def cmd_purge_channel(message: Message, session: AsyncSession) -> None:
    """Очистить каталог и матчи по пользовательскому каналу (не seed)."""
    if not message.text or len(message.text.split()) < 2:
        await message.answer("Использование: /purge_channel @djsjs")
        return
    channel_name = message.text.split(maxsplit=1)[1].strip()
    channel_repo = ChannelRepository(session)
    result = await channel_repo.purge_channel_feed(channel_name)
    if result.get("error") == "not_found":
        await message.answer(f"Канал {channel_name} не найден в мониторинге.")
        return
    if result.get("error") == "seed_channel":
        await message.answer("Seed-каналы через эту команду не чистятся.")
        return
    await session.commit()
    await message.answer(
        f"🧹 Канал {channel_name} очищен:\n"
        f"• каталог деактивирован: {result['catalog']}\n"
        f"• карточек удалено: {result['sent']}\n"
        f"• processed_pairs: {result['processed']}"
    )


@router.message(Command("dedupe_catalog"), AdminFilter())
async def cmd_dedupe_catalog(message: Message, session: AsyncSession) -> None:
    """Убрать дубликаты в каталоге (одинаковое название или ссылка)."""
    repo = OpportunityCatalogRepository(session)
    removed = await repo.deactivate_duplicates()
    await session.commit()
    await message.answer(f"🧹 Дубликаты в каталоге: деактивировано {removed} записей.")


@router.message(Command("sync_webapp"), AdminFilter())
async def cmd_sync_webapp(message: Message) -> None:
    """Обновить URL Mini App в Telegram (Menu Button)."""
    settings = get_settings()
    url = settings.resolved_webapp_url
    if not url:
        await message.answer(
            "PUBLIC_BASE_URL не задан в .env.\n"
            "Запусти setup_tunnel.ps1 и добавь URL."
        )
        return

    reset_menu_cache()
    await setup_telegram_webapp(message.bot, force=True)
    await sync_user_menu_button(message.bot, message.chat.id, force=True)

    await message.answer(
        "✅ Menu Button обновлён\n\n"
        f"URL: <code>{url}</code>\n\n"
        "Если в Telegram всё ещё Error 1033 на старый адрес:\n"
        "1. Отправь /app и нажми кнопку <b>Open Mini App</b> в сообщении\n"
        "2. BotFather → твой бот → Bot Settings → Menu Button → "
        "Open Web App → вставь URL выше\n"
        "3. Закрой чат с ботом и открой заново",
        parse_mode="HTML",
    )


def _format_user_ref(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f"id {user.telegram_id}"


def _split_messages(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit and current:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


@router.message(Command("user_channels"), AdminFilter())
async def cmd_user_channels(message: Message, session: AsyncSession) -> None:
    """Все каналы, которые пользователи добавили через /add_channel."""
    channel_repo = ChannelRepository(session)
    rows = await channel_repo.list_user_channels_with_owners()

    if not rows:
        await message.answer("Пока ни один пользователь не добавил каналы.")
        return

    by_user: dict[int, dict] = {}
    for uc, user in rows:
        bucket = by_user.setdefault(
            user.id,
            {"user": user, "channels": []},
        )
        bucket["channels"].append(uc)

    lines = [f"📡 Каналы пользователей ({len(rows)} шт., {len(by_user)} чел.)\n"]
    for bucket in by_user.values():
        user = bucket["user"]
        channels = bucket["channels"]
        lines.append(f"\n👤 {_format_user_ref(user)} · {len(channels)} кан.")
        for i, uc in enumerate(channels, 1):
            title = uc.channel_title or uc.channel_identifier
            lines.append(f"  {i}. {uc.channel_identifier} — {title}")

    monitored = await channel_repo.list_user_added_monitored()
    if monitored:
        lines.append(f"\n\n📋 В мониторинге (user-added): {len(monitored)}")
        for ch in monitored:
            status = "ok" if ch.is_accessible else "нет доступа"
            lines.append(f"  • {ch.channel_identifier} ({ch.source_count} юз.) — {status}")

    for chunk in _split_messages("\n".join(lines)):
        await message.answer(chunk)


@router.message(Command("training_stats"), AdminFilter())
async def cmd_training_stats(message: Message, session: AsyncSession) -> None:
    """Сколько данных собрано для будущего обучения."""
    settings = get_settings()
    repo = TrainingRepository(session)
    total = await repo.count_total()
    by_task = await repo.count_by_task()

    if not total:
        await message.answer(
            "📚 Training data: пока пусто.\n\n"
            f"Сбор: {'✅ включён' if settings.training_data_enabled else '❌ выключен'}\n"
            "Данные появятся после классификации постов и отправки карточек."
        )
        return

    lines = [
        f"📚 Training data: {total} сэмплов",
        f"Сбор: {'✅ включён' if settings.training_data_enabled else '❌ выключен'}",
        f"Папка экспорта: {settings.training_data_dir}",
        "",
        "По задачам:",
    ]
    task_labels = {
        "classify": "классификация постов",
        "match": "подбор пользователю",
        "relevance": "LLM relevance (если включён)",
        "categories": "категории из профиля",
    }
    for task, count in by_task.items():
        label = task_labels.get(task, task)
        lines.append(f"  • {task} ({label}): {count}")

    lines.append("\nЭкспорт: /export_training или /export_training classify")
    await message.answer("\n".join(lines))


@router.message(Command("campaign_preview"), AdminFilter())
async def cmd_campaign_preview(message: Message, session: AsyncSession) -> None:
    """Превью кампании — только тебе."""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /campaign_preview kbtu_startup_camp [perfect|high|partial]")
        return
    args = parts[1].split()
    slug = args[0]
    tier = args[1] if len(args) > 1 else "perfect"
    try:
        campaign = load_campaign(slug)
    except FileNotFoundError:
        await message.answer(f"Кампания «{slug}» не найдена в data/campaigns/")
        return
    from services.promo_campaign import campaign_keyboard

    await message.answer(
        format_campaign_message(campaign, tier=tier),
        parse_mode="HTML",
        reply_markup=campaign_keyboard(slug),
    )


@router.message(Command("campaign_send"), AdminFilter())
async def cmd_campaign_send(message: Message, session: AsyncSession) -> None:
    """Разослать промо-кампанию списку user db id из JSON."""
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "Использование:\n"
            "/campaign_preview kbtu_startup_camp\n"
            "/campaign_send kbtu_startup_camp\n"
            "/campaign_send kbtu_startup_camp force — повторно\n"
            "/campaign_stats kbtu_startup_camp"
        )
        return
    slug = parts[1]
    force = len(parts) > 2 and parts[2].lower() == "force"
    await message.answer(f"⏳ Рассылаю кампанию <code>{slug}</code>…", parse_mode="HTML")
    try:
        stats = await run_campaign(slug, force=force)
    except FileNotFoundError:
        await message.answer(f"Кампания «{slug}» не найдена.")
        return
    await message.answer(
        f"✅ Кампания <code>{slug}</code>\n\n"
        f"📤 отправлено: {stats.get('sent', 0)}\n"
        f"⏭ пропущено (уже было): {stats.get('skipped', 0)}\n"
        f"🚫 недоступны: {stats.get('unreachable', 0)}\n"
        f"❓ нет в базе: {stats.get('missing', 0)}\n"
        f"❌ ошибки: {stats.get('error', 0)}\n\n"
        f"Трекинг: /campaign_stats {slug}",
        parse_mode="HTML",
    )


@router.message(Command("campaign_stats"), AdminFilter())
async def cmd_campaign_stats(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Использование: /campaign_stats kbtu_startup_camp")
        return
    slug = parts[1].strip()
    try:
        data = await get_campaign_stats(slug)
    except Exception as exc:
        await message.answer(f"Ошибка: {exc}")
        return
    await message.answer(format_campaign_stats_report(data), parse_mode="HTML")


@router.message(Command("maintenance_resend"), AdminFilter())
async def cmd_maintenance_resend(message: Message) -> None:
    """Извинение пользователям, зарегистрированным за последние N дней."""
    parts = (message.text or "").split()
    days = 7
    force = False
    welcome = False
    dry_run = False
    for part in parts[1:]:
        lower = part.lower()
        if lower == "force":
            force = True
        elif lower == "welcome":
            welcome = True
        elif lower == "dry":
            dry_run = True
        elif lower.isdigit():
            days = max(1, int(lower))

    await message.answer(
        f"⏳ Рассылка техобслуживания за {days} дн."
        f"{' · dry-run' if dry_run else ''}…",
        parse_mode="HTML",
    )
    stats = await send_maintenance_apology(
        days=days,
        force=force,
        resend_welcome=welcome,
        dry_run=dry_run,
    )
    await message.answer(
        f"{'🔍 Dry-run' if dry_run else '✅ Готово'}\n\n"
        f"🎯 в очереди: {stats['target']}\n"
        f"📤 отправлено: {stats['sent']}\n"
        f"⏭ пропущено: {stats['skipped']}\n"
        f"🚫 недоступны: {stats['unreachable']}\n"
        f"❌ ошибки: {stats['error']}",
        parse_mode="HTML",
    )


@router.message(Command("db_check"), AdminFilter())
async def cmd_db_check(message: Message) -> None:
    """Проверка Supabase pooler и текущего DATABASE_URL."""
    from urllib.parse import urlparse

    from db.base import configure_supabase_pooler, engine
    from db.pooler_probe import extract_project_ref, probe_working_database_url
    from sqlalchemy import text

    settings = get_settings()
    raw = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    ref = extract_project_ref(settings.database_url)

    lines = [
        "🗄 <b>Database check</b>",
        f"host: <code>{parsed.hostname}:{parsed.port}</code>",
        f"user: <code>{parsed.username}</code>",
        f"project ref: <code>{ref or '?'}</code>",
    ]

    try:
        working = await probe_working_database_url(settings.database_url)
        if working != settings.database_url:
            wp = urlparse(working.replace("postgresql+asyncpg://", "postgresql://", 1))
            lines.append(f"probe OK: <code>{wp.hostname}:{wp.port}</code>")
            lines.append("→ задай <code>SUPABASE_POOLER_HOST</code> в Railway")
        await configure_supabase_pooler()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        lines.append("✅ SELECT 1 OK")
    except Exception as exc:
        lines.append(f"❌ {type(exc).__name__}: {exc}")
        lines.append(
            "\nSupabase → Connect → URI → скопируй host в "
            "<code>SUPABASE_POOLER_HOST</code> и Redeploy"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("community_stats"), AdminFilter())
async def cmd_community_stats(message: Message) -> None:
    stats = await get_community_invite_stats()
    total = stats["totalUsers"]
    invited = stats["invitedUsers"]
    pct = round(invited / total * 100, 1) if total else 0
    await message.answer(
        "👥 <b>Сообщество Lumo</b>\n\n"
        f"Пользователей бота: {total}\n"
        f"Получили приглашение: {invited} ({pct}%)\n"
        f"Batch: <code>{stats['batch']}</code>\n\n"
        "Разослать: /community_invite\n"
        "Повторно всем: /community_invite force\n"
        "Проверка без отправки: /community_invite dry",
        parse_mode="HTML",
    )


@router.message(Command("community_invite"), AdminFilter())
async def cmd_community_invite(message: Message) -> None:
    """Разослать приглашение в сообщество всем пользователям бота."""
    parts = (message.text or "").split()
    force = "force" in [p.lower() for p in parts[1:]]
    dry_run = "dry" in [p.lower() for p in parts[1:]]

    if not community_join_inline():
        settings = get_settings()
        await message.answer(
            "❌ <b>COMMUNITY_TELEGRAM_URL неверный</b>\n\n"
            f"Сейчас: <code>{settings.community_telegram_url or '(пусто)'}</code>\n\n"
            "Railway → Variables:\n"
            "<code>COMMUNITY_TELEGRAM_URL=https://t.me/+твоя_ссылка</code>\n"
            "или <code>https://t.me/LumoCommunity</code>\n"
            "Redeploy → снова /community_invite",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"⏳ Рассылка приглашения в сообщество"
        f"{' · dry-run' if dry_run else ''}…",
        parse_mode="HTML",
    )
    stats = await send_community_invite(force=force, dry_run=dry_run)
    await message.answer(
        f"{'🔍 Dry-run' if dry_run else '✅ Готово'}\n\n"
        f"🎯 в очереди: {stats['target']}\n"
        f"📤 отправлено: {stats['sent']}\n"
        f"⏭ пропущено (уже слали): {stats['skipped']}\n"
        f"🚫 недоступны: {stats['unreachable']}\n"
        f"❌ ошибки: {stats['error']}",
        parse_mode="HTML",
    )


@router.message(Command("export_training"), AdminFilter())
async def cmd_export_training(message: Message) -> None:
    """Экспорт JSONL для fine-tuning."""
    parts = (message.text or "").split(maxsplit=1)
    task = parts[1].strip() if len(parts) > 1 else None
    if task and task not in {"classify", "match", "relevance", "categories"}:
        await message.answer(
            "Использование: /export_training [classify|match|relevance|categories]"
        )
        return

    await message.answer("⏳ Экспортирую training data…")
    try:
        path = await export_training_jsonl(task=task)
    except Exception as exc:
        await message.answer(f"❌ Ошибка экспорта: {exc}")
        return

    if not path.exists() or path.stat().st_size == 0:
        await message.answer("Файл пустой — пока нет данных для экспорта.")
        return

    await message.answer_document(
        FSInputFile(path),
        caption=f"📦 {path.name}\nСтрок: {sum(1 for _ in path.open(encoding='utf-8'))}",
    )

