import os
import time
import json
import hashlib
import base64
import hmac

import requests
from dotenv import load_dotenv

load_dotenv()


def gen_sign(timestamp, secret):
    # 拼接timestamp和secret
    string_to_sign = "{}\n{}".format(timestamp, secret)
    hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256)
    hmac_code = hmac_code.digest()
    # 对结果进行base64处理
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return sign


def _send_feishu_alert(msg_body: dict, webhook: str = None, secret: str = None):
    if webhook is None:
        webhook = os.getenv("FEISHU_WEBHOOK")
    if secret is None:
        secret = os.getenv("FEISHU_SECRET")

    headers = {"Content-Type": "application/json"}
    timestamp = int(time.time())
    sign = gen_sign(timestamp, secret)
    msg_body.update(
        {
            "timestamp": timestamp,
            "sign": sign,
        }
    )
    res = requests.post(webhook, data=json.dumps(msg_body), headers=headers, timeout=30)
    res.raise_for_status()
    return res.json()


def send_feishu_messages(title: str, messages: list, webhook: str = None, secret: str = None):
    msg_body = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": messages,
                }
            }
        },
    }
    _send_feishu_alert(msg_body, webhook=webhook, secret=secret)
