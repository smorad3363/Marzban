from requests import post


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    try:
        response = post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={"chat_id": chat_id, "parse_mode": "HTML", "text": text},
            timeout=10,
        )
    except Exception as exc:
        raise RuntimeError("Could not reach Telegram") from exc

    if not response.ok:
        try:
            description = response.json().get("description", "Telegram rejected the request")
        except ValueError:
            description = "Telegram rejected the request"
        raise RuntimeError(description)
