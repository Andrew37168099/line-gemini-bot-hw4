from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import os
from google import genai  # 確保是 google-genai
from linebot.models import StickerMessage
from linebot.models import ImageMessage, VideoMessage, LocationMessage
import json
from datetime import datetime

HISTORY_FILE = "chat_history.json"

# 載入 .env 變數
load_dotenv()

# 初始化 LINE Bot
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 初始化 Gemini 客戶端
client = genai.Client(api_key="AIzaSyCZUj6f-UREhevfokLVgVx82dqKZOFWenY")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "LINE + Gemini Bot using google-genai is running."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@app.route("/history", methods=["GET"])
def get_history():
    if not os.path.exists(HISTORY_FILE):
        return {"history": []}
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
    return {"history": history}

@app.route("/history", methods=["DELETE"])
def delete_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    return {"message": "History cleared."}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    print(f"[使用者傳來] {user_msg}")
    
    try:
        response = client.models.generate_content(
            model="models/gemini-2.0-flash",
            contents=user_msg
        )
        reply_text = response.candidates[0].content.parts[0].text
        print(f"[Gemini 回覆] {reply_text}")
    except Exception as e:
        reply_text = f"⚠️ Gemini 發生錯誤：{e}"
        print(reply_text)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )
    save_history(user_msg, reply_text)

@handler.add(MessageEvent, message=StickerMessage)
def handle_sticker(event):
    reply = "這張貼圖不錯 😎（目前我只懂文字哦）"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    reply = "📸 我收到一張圖片！不過我目前只看得懂文字～"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@handler.add(MessageEvent, message=VideoMessage)
def handle_video(event):
    reply = "🎥 收到影片了！看起來你拍了點什麼？但我只能讀文字啦～"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    title = event.message.title or "未知地點"
    latitude = event.message.latitude
    longitude = event.message.longitude

    reply = f"📍 你傳來的位置是：{title}\n緯度：{latitude}\n經度：{longitude}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

def save_history(user_msg, gemini_reply):
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)

    history.append({
        "timestamp": datetime.now().isoformat(),
        "user_message": user_msg,
        "gemini_reply": gemini_reply
    })

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    app.run()
