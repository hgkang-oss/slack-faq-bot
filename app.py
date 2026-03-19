import os
import csv
import io
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

SLACK_BOT_TOKEN = os.environ["xoxb-806575416260-10729989877142-oaCqS3DLoHTEGDZoDkRFocwG"]
SLACK_APP_TOKEN = os.environ["xapp-1-A0AMBCHJ5TM-10730114515894-6b499bf66e5456ba0813c7718cc9a5eadf2dda814612ebb60fe8c6a3ee113fbd"]
TARGET_CHANNEL_ID = os.environ["C01NZMP9059"]
GOOGLE_SHEET_ID = os.environ["1Y69lnZ2AJWOQREvOTje1SSYM9gIm1Pq28_N3QclIvxk"]
FALLBACK_GROUP_ID = os.environ["S056CF3DBQR"]

CSV_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv&gid=0"

app = App(token=SLACK_BOT_TOKEN)

def load_faq():
    response = requests.get(CSV_URL, timeout=10)
    response.raise_for_status()
    decoded = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    faq_list = []
    for row in reader:
        keywords = [
            (row.get("keywords1") or "").strip(),
            (row.get("keywords2") or "").strip(),
            (row.get("keywords3") or "").strip(),
        ]
        keywords = [k for k in keywords if k]
        answer = (row.get("answer") or "").strip()

        if keywords and answer:
            faq_list.append({
                "keywords": keywords,
                "answer": answer
            })

    return faq_list

def match_faq(text, faq_list):
    text = (text or "").strip()
    best_answer = None
    best_score = 0

    for faq in faq_list:
        score = 0
        for kw in faq["keywords"]:
            if kw in text:
                score += 1

        if score > best_score:
            best_score = score
            best_answer = faq["answer"]

    if best_score >= 2:
        return best_answer
    return None

@app.event("message")
def handle_message_events(client, event, logger):
    try:
        if event.get("channel") != TARGET_CHANNEL_ID:
            return
        if event.get("bot_id"):
            return
        if event.get("subtype"):
            return

        text = event.get("text", "")
        if not text:
            return

        faq_list = load_faq()
        answer = match_faq(text, faq_list)

        if answer:
            client.chat_postMessage(
                channel=event["channel"],
                thread_ts=event["ts"],
                text=answer
            )
        else:
            client.chat_postMessage(
                channel=event["channel"],
                thread_ts=event["ts"],
                text=(
                    "등록된 FAQ에서 답변을 찾지 못했어요.\n"
                    f"<!subteam^{FALLBACK_GROUP_ID}> 확인 부탁드립니다 🙏"
                )
            )
    except Exception as e:
        logger.exception(f"Error handling message: {e}")

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()