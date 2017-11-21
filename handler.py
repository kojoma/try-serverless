# -*- coding: utf-8 -*-

"""
指定されたログメッセージをSlackに投稿する関数です。
ログメッセージはCloudWatch Logsのログを想定しています。

# 使い方

```python
import boto3

log_event = {
    'id': 1234567890
    'timestamp': 1234567890
    'message': "log message"
}
payload = {
    'logGroup': "log_group_name",
    'logStream': "log_stream_name",
    'logEvent': log_event
}
lambda_client = boto3.client('lambda')
lambda_client.invoke(
    FunctionName = "notify-slack",
    InvocationType = "Event",
    Payload = json.dumps(payload)
)
```

# log_eventのmessageについて

message内が下記のようなJSON形式の場合、ログレベルに応じて色をつけるなどしてSlackに投稿します。

```json
{
    "metadata": {},
    "level": "error",
    "datetime": "2017-01-01 00:00:00.000",
    "content": "log message"
}
```
"""

from __future__ import print_function

import json
import logging
import os
import base64
import zlib
import datetime

from urllib2 import Request, urlopen, URLError, HTTPError

HOOK_URL = os.environ['hookUrl']
SLACK_CHANNEL = os.environ['slackChannel']

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def notify_slack(event, context):
    logger.info(json.dumps(event))

    slack_message = build_message(event['logGroup'], event['logStream'], event['logEvent'])
    req = Request(HOOK_URL, json.dumps(slack_message))

    try:
        response = urlopen(req)
        response.read()
        logger.info("Message posted to %s", slack_message['channel'])
    except HTTPError as e:
        logger.error("Request failed: %d %s", e.code, e.reason)
    except URLError as e:
        logger.error("Server connection failed: %s", e.reason)

def build_message(log_group, log_stream, log_event):
    ref_time = log_event['timestamp']
    ref_id = log_event['id']

    url = "https://ap-northeast-1.console.aws.amazon.com/cloudwatch/home?region=ap-northeast-1#logEventViewer:group=%s;stream=%s;reftime=%s;refid=%s" % (log_group, log_stream, ref_time, ref_id)

    try:
        message_json = json.loads(log_event['message'])

        # json形式の場合は、ログから通知用の情報を抜き出す
        time = message_json['datetime']
        level = message_json['level']
        log_text = message_json['content']
        color = get_color(level)
        text = "%s\n%s / %s で `%s` ログがあります(<%s|詳細はこちら>)" % (time, log_group, log_stream, level, url)
    except:
        # json形式でない場合は、可能な範囲で抜き出し、難しい項目は擬似的な値を入れたりする
        date = datetime.datetime.fromtimestamp(int(str(ref_time)[:10]))
        time = str(date)
        log_text = log_event['message']
        color = get_color("-")
        text = "%s\n%s / %s でログがあります(<%s|詳細はこちら>)" % (time, log_group, log_stream, url)

    slack_message = {
        'username': "log notification",
        'channel': SLACK_CHANNEL,
        'text': text,
        'mrkdwn': "true",
        'attachments': [
            {
                'text': "%s" % (log_text),
                'color': "%s" % (color)
            }
        ]
    }

    return slack_message

def get_color(log_level):
    if log_level == "error":
        color = "danger"
    elif log_level == "warn":
        color = "warning"
    else:
        color = "normal"

    return color
