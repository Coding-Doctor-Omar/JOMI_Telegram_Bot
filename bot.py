from flask import Flask, request
from curl_cffi import requests as cureq
import requests
import os

app = Flask(__name__)

TELEGRAM_API = "https://api.telegram.org/bot"
BOT_TOKEN = os.environ.get("jomi_downloader_bot_token")
VALID_COMMANDS = ["/start", "/how_to_use", "/source_code"]

def unlock_video(vid_url: str) -> tuple:
    res = cureq.get(vid_url, impersonate="edge")
    separator = '"contentType":"video/mp4"'

    try:
        _224p_ = [chunk.split('"url":"')[-1].split('.bin')[0] + '.mp4' for chunk in res.text.split(separator) if '"height":224' in chunk and '.bin' in chunk and 'image' not in chunk][0]
        _360p_ = [chunk.split('"url":"')[-1].split('.bin')[0] + '.mp4' for chunk in res.text.split(separator) if '"height":360' in chunk and '.bin' in chunk and 'image' not in chunk][0]
        _540p_ = [chunk.split('"url":"')[-1].split('.bin')[0] + '.mp4' for chunk in res.text.split(separator) if '"height":540' in chunk and '.bin' in chunk and 'image' not in chunk][0]
        _720p_ = [chunk.split('"url":"')[-1].split('.bin')[0] + '.mp4' for chunk in res.text.split(separator) if '"height":720' in chunk and '.bin' in chunk and 'image' not in chunk][0]
        _1080p_ = [chunk.split('"url":"')[-1].split('.bin')[0] + '.mp4' for chunk in res.text.split(separator) if '"height":1080' in chunk and '.bin' in chunk and 'image' not in chunk][0]
    except Exception:
        return {}, ""
    else:
        return {
            "224p": _224p_,
            "360p": _360p_,
            "540p": _540p_,
            "720p": _720p_,
            "1080p": _1080p_
        }, res.text

def get_subtitles(page_html: str) -> bytes:
    content = ""

    try:
        video_id = page_html.split("/embed/iframe/")[-1].split(",")[0].replace('"', "").split("}")[0].strip()
        subtitle_data_url = f"https://fast.wistia.com/embed/captions/{video_id}.json"

        res = cureq.get(subtitle_data_url, impersonate="edge")
        data = res.json()
    except Exception:
        return b""

    subtitles = [sub["hash"]["lines"] for sub in data["captions"] if sub["familyName"] == "English"][0]

    for ind, line in enumerate(subtitles):
        line_num = ind + 1
        start_raw = line["start"]
        end_raw = line["end"]

        start_hrs = int(start_raw // 3600)
        start_mins = int((start_raw % 3600) // 60)
        start_secs = int(start_raw % 60)
        start_ms = int((start_raw - int(start_raw)) * 1000)
        start_string = f"{start_hrs:02}:{start_mins:02}:{start_secs:02},{start_ms:03}"

        end_hrs = int(end_raw // 3600)
        end_mins = int((end_raw % 3600) // 60)
        end_secs = int(end_raw % 60)
        end_ms = int((end_raw - int(end_raw)) * 1000)
        end_string = f"{end_hrs:02}:{end_mins:02}:{end_secs:02},{end_ms:03}"

        time_string = f"{start_string} --> {end_string}"
        line_text = "\n".join(line["text"])

        block_text = f"{line_num}\n{time_string}\n{line_text}\n\n"

        content += block_text

    return bytes(content, encoding="utf-8")

def msg_is_valid(message: str) -> bool:
    if message in VALID_COMMANDS:
        return True

    message_words = message.split()
    first_link = [word.strip() for word in message_words if word.startswith("https")]

    if not first_link:
        return False

    if "jomi.com" not in first_link[0] or "/article" not in first_link[0]:
        return False

    return True

def send_msg(chat_id: int, msg: str, parse_mode=None) -> None:
    method = "/sendMessage"

    if parse_mode:
        message = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": parse_mode
        }
    else:
        message = {
            "chat_id": chat_id,
            "text": msg
        }

    res = requests.post(url=f"{TELEGRAM_API}{BOT_TOKEN}{method}", params=message)

def handle_start_command(chat_id: int) -> None:
    message = "Hello there! Welcome to JOMI BOT!\nBelow is a list of supported commands. To use the commands, check my menu or simply type the command as a message.\n\n/how_to_use  ---> Teaches you how to use me.\n/source_code ---> Sends you my source code link on GitHub."
    send_msg(chat_id=chat_id, msg=message)

def handle_how_to_use_command(chat_id: int) -> None:
    message = "To unlock a JOMI video, just send me the link for the video page without anything else in the message. JOMI video pages have links with a structure like this:\n\nhttps://jomi.com/article/..."
    send_msg(chat_id=chat_id, msg=message)

def handle_source_code_command(chat_id: int) -> None:
    message = "Hmm, so you are interested. Very well, here is my source code on GitHub:\n\nhttps://github.com/Coding-Doctor-Omar/JOMI_Telegram_Bot"
    send_msg(chat_id=chat_id, msg=message)

def send_unlocked_content(chat_id: int, user_msg: str) -> None:
    video_url = [word.strip() for word in user_msg.split() if word.startswith("https")][0]
    unlocked_urls, page_html = unlock_video(vid_url=video_url)
    subtitles = get_subtitles(page_html=page_html)

    if not unlocked_urls or not subtitles:
        send_msg(chat_id=chat_id, msg="An error has occurred while processing the video link. Either the link is incorrect or a backend server error has occurred. Please try again.")
        return

    message = rf"""Voila! Your video has been unlocked! Choose the quality that fits you from the list below:

<a href="{unlocked_urls['224p']}">Video (224p)</a>
<a href="{unlocked_urls['360p']}">Video (360p)</a>
<a href="{unlocked_urls['540p']}">Video (540p)</a>
<a href="{unlocked_urls['720p']}">HD Video (720p)</a>
<a href="{unlocked_urls['1080p']}">Full HD Video (1080p)</a>"""

    send_msg(chat_id=chat_id, msg=message, parse_mode="HTML")

    # Send subtitles
    method = "/sendDocument"
    attachment_description = {
        "chat_id": chat_id,
        "caption": "Here is the subtitles file. Click on the three dots button on the top right of the message and select 'Save to Downloads'.\nIt will be saved in the Telegram folder on your phone storage.\n\nThis would only be useful if you want to download the video and view it offline."
    }
    file = {
        "document": ("subtitles.srt", subtitles)
    }

    res = requests.post(url=f"{TELEGRAM_API}{BOT_TOKEN}{method}", data=attachment_description, files=file)



@app.route("/telegram", methods=["POST"])
def process_message():
    actions = {
        "/start": handle_start_command,
        "/how_to_use": handle_how_to_use_command,
        "/source_code": handle_source_code_command
    }

    update = request.get_json()

    if "message" not in update:
        return "OK", 200

    try:
        chat_id = update["message"]["chat"]["id"]
        user_message = update["message"]["text"]
    except Exception:
        return "OK", 200

    if msg_is_valid(user_message):
        if user_message in VALID_COMMANDS:
            action = actions[user_message]
            action(chat_id=chat_id)
            return "OK", 200
        else:
            send_msg(chat_id=chat_id, msg="Processing video link...")
            send_unlocked_content(chat_id=chat_id, user_msg=user_message)
            return "OK", 200

    else:
        send_msg(chat_id=chat_id, msg="The message you sent me is not a valid command or a valid link for any JOMI video page. Please try again.")
        return "OK", 200


@app.route("/")
def home():
    return "<h1>JOMI BOT is properly deployed!</h1>", 200


if __name__ == "__main__":
    app.run()
