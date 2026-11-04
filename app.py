
import os
import requests
from flask import Flask, request, jsonify
from datetime import date

app = Flask(__name__)

TOKEN = os.environ["BOT_TOKEN"]
PUBLIC_URL = os.environ["WEBHOOK_URL"]
API = "https://www.thesportsdb.com/api/v1/json/123"
LEAGUE_ID = "4328"

TG = f"https://api.telegram.org/bot{TOKEN}"


def send(chat_id, text, keyboard=True):
    data = {"chat_id": chat_id, "text": text}
    if keyboard:
        data["reply_markup"] = {
            "keyboard": [
                ["⚽ Результаты", "📅 Расписание"],
                ["🏆 Таблица", "👥 Команда"],
                ["🔔 Уведомления"]
            ],
            "resize_keyboard": True
        }
    requests.post(TG + "/sendMessage", json=data, timeout=20)


def sports(endpoint, params=None):
    try:
        r = requests.get(
            f"{API}/{endpoint}",
            params=params,
            timeout=20
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return {}


def events_text(events):
    if not events:
        return "Матчи не найдены."

    result = []
    for e in events[:12]:
        home = e.get("strHomeTeam", "?")
        away = e.get("strAwayTeam", "?")
        hs = e.get("intHomeScore")
        aws = e.get("intAwayScore")
        score = f"{hs} : {aws}" if hs is not None and aws is not None else "VS"

        result.append(
            f"⚽ {home} — {away}\n"
            f"📊 {score}\n"
            f"📅 {e.get('dateEvent', '?')}"
        )

    return "\n\n".join(result)


def handle_message(message):
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if text.startswith("/start"):
        send(chat_id, "⚽ Football Bot!\nВыбери раздел.")
        return

    if text == "⚽ Результаты" or text == "/today":
        data = sports("eventsday.php", {
            "d": date.today().isoformat(),
            "s": "Soccer"
        })
        send(chat_id, "⚽ Матчи сегодня:\n\n" +
             events_text(data.get("events")))
        return

    if text == "📅 Расписание" or text == "/fixtures":
        data = sports("eventsnextleague.php", {"id": LEAGUE_ID})
        send(chat_id, "📅 Ближайшие матчи АПЛ:\n\n" +
             events_text(data.get("events")))
        return

    if text == "🏆 Таблица" or text == "/table":
        data = sports("lookuptable.php", {"l": LEAGUE_ID})
        rows = data.get("table") or []

        if not rows:
            send(chat_id, "Турнирная таблица сейчас недоступна.")
            return

        lines = ["🏆 Таблица АПЛ:\n"]
        for t in rows:
            lines.append(
                f"{t.get('intRank', '?')}. "
                f"{t.get('strTeam', '?')} — "
                f"{t.get('intPoints', '?')} очков"
            )

        send(chat_id, "\n".join(lines))
        return

    if text.startswith("/team "):
        name = text[6:].strip()
        data = sports("searchteams.php", {"t": name})
        teams = data.get("teams") or []

        if not teams:
            send(chat_id, "Команда не найдена.")
            return

        t = teams[0]
        send(
            chat_id,
            f"👥 {t.get('strTeam', '?')}\n"
            f"🏟 Стадион: {t.get('strStadium', '?')}\n"
            f"🌍 Страна: {t.get('strCountry', '?')}\n"
            f"🏆 Лига: {t.get('strLeague', '?')}"
        )
        return

    if text == "👥 Команда":
        send(chat_id, "Введи команду командой:\n/team Arsenal")
        return

    if text == "🔔 Уведомления":
        send(
            chat_id,
            "🔔 Уведомления о голах пока не подключены.\n"
            "Для них нужен отдельный источник live-данных."
        )
        return

    send(chat_id, "Выбери раздел в меню или напиши /start.")


@app.route("/", methods=["GET"])
def home():
    return "Football Bot is running!"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message")

    if message and message.get("text"):
        try:
            handle_message(message)
        except Exception as error:
            print("Bot error:", error)

    return jsonify({"ok": True})


# Register Telegram webhook when the service starts
try:
    response = requests.post(
        TG + "/setWebhook",
        json={"url": PUBLIC_URL},
        timeout=20
    )
    print("Webhook:", response.text)
except requests.RequestException as error:
    print("Webhook setup error:", error)
                      
