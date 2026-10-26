from html import escape

from bot.models import ChatSettings, ReplyMode

HELP = """<b>OnlyComment</b>

В группе обсуждений канала я удаляю сообщения, которые не являются ответами. Так все разговоры остаются в комментариях под постами.

<b>Как подключить</b>
1. Привяжите группу обсуждений к каналу.
2. Добавьте меня в группу и сделайте админом с правом «Удаление сообщений».
3. Владелец бота добавляет ID группы в <code>ALLOWED_CHAT_IDS</code>.

<b>Команды в личке</b>
/settings — настройки ваших чатов
/whereami — ваш user ID
/status — состояние бота (для владельцев)

<b>Команды в группе</b> (для админов)
/settings — меню настроек
/on, /off — включить или выключить модерацию
/mode any|thread — какие ответы разрешены
/warn on|off|секунды — предупреждение об удалении
/logchat ID|off — куда присылать журнал удалений
/whereami — ID этого чата"""

YOUR_ID = "Ваш user ID: <code>{user_id}</code>"
CHAT_ID = "ID этого чата: <code>{chat_id}</code>"

LEFT_UNKNOWN_CHAT = (
    "Меня добавили в чат «{title}» (<code>{chat_id}</code>), но его нет в ALLOWED_CHAT_IDS, "
    "поэтому я из него вышел. Если это ваш чат, добавьте ID в .env и пригласите меня снова."
)
CHAT_MIGRATED = (
    "Группа «{title}» стала супергруппой, её ID сменился: <code>{old_id}</code> → <code>{new_id}</code>. "
    "Обновите ALLOWED_CHAT_IDS в .env и перезапустите бота."
)

STATUS_HEADER = "<b>Режим:</b> {mode}\n<b>Чатов в списке:</b> {count}"
STATUS_NO_CHATS = "ALLOWED_CHAT_IDS пуст: бот нигде не модерирует."
STATUS_CHAT_OK = "✅ {title} (<code>{chat_id}</code>)"
STATUS_CHAT_NO_RIGHTS = "⚠️ {title} (<code>{chat_id}</code>): нет права удалять сообщения"
STATUS_CHAT_ERROR = "❌ <code>{chat_id}</code>: нет доступа к чату"

CHOOSE_CHAT = "Выберите чат для настройки:"
NO_CHATS = "Нет чатов, которые вы можете настраивать."
NO_RIGHTS = "Настраивать этот чат могут только его админы и владельцы бота."
MESSAGE_GONE = "Это меню устарело, откройте /settings заново."

ENABLED = "Модерация включена."
DISABLED = "Модерация выключена."
MODE_SET = "Режим: {mode}."
MODE_USAGE = "Использование: /mode any или /mode thread"
WARN_ON = "Предупреждения включены, удаляются через {ttl} с."
WARN_OFF = "Предупреждения выключены."
WARN_USAGE = "Использование: /warn on, /warn off или /warn 15 (секунды, от 1 до 300)"
LOG_SET = "Журнал удалений будет приходить в <code>{chat_id}</code>."
LOG_OFF = "Журнал удалений выключен."
LOG_USAGE = "Использование: /logchat -1001234567890 или /logchat off"
LOG_UNREACHABLE = "Не могу писать в <code>{chat_id}</code>. Добавьте меня туда или напишите мне в личку /start."
LOG_TEST = "Сюда будет приходить журнал удалений из «{title}»."

WARNING = "{author}, здесь можно писать только ответами в комментариях к постам. Сообщение удалено."
LOG_ENTRY = "🗑 <b>{chat}</b>\nОт: {author}\nТип: {content_type}\n{text}"

MODE_NAMES = {
    ReplyMode.ANY: "ответ на любое сообщение",
    ReplyMode.THREAD: "только ветки постов",
}

BTN_ENABLED = "{flag} Модерация"
BTN_MODE = "Режим: {mode}"
BTN_EXEMPT_ADMINS = "{flag} Не трогать админов"
BTN_EXEMPT_CHANNEL = "{flag} Не трогать канал"
BTN_WARN = "{flag} Предупреждать"
BTN_WARN_TTL = "⏱ Предупреждение живёт {ttl} с"
BTN_LOG_HERE = "📝 Журнал: присылать мне"
BTN_LOG_OFF = "📝 Журнал: выключить"
BTN_BACK = "« К списку чатов"
BTN_CLOSE = "Закрыть"


def flag(value: bool) -> str:
    return "✅" if value else "❌"


def settings_text(settings: ChatSettings, title: str) -> str:
    log = f"<code>{settings.log_chat_id}</code>" if settings.log_chat_id else "выключен"
    return (
        f"<b>Настройки «{escape(title)}»</b>\n\n"
        f"Модерация: {'включена' if settings.enabled else 'выключена'}\n"
        f"Режим: {MODE_NAMES[settings.reply_mode]}\n"
        f"Админы: {'не трогаю' if settings.exempt_admins else 'тоже модерирую'}\n"
        f"Связанный канал: {'не трогаю' if settings.exempt_channel else 'тоже модерирую'}\n"
        f"Предупреждение: {f'да, {settings.warn_ttl} с' if settings.warn_enabled else 'нет'}\n"
        f"Журнал: {log}"
    )
