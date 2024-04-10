# Feishu Alert Bots

## Setup

- feishu webhook docs: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot#3c6592d6

```bash
pip install -r requirements.txt
cp .env.example .env
# change settings in .env
```

## Deployment

```bash
# crotab: run at 13:00 every day
# crontab -e
0 13 * * * /usr/bin/python3 /path/to/feishu-alert-bots/daily_arxiv.py
```

## TODO

- [ ] [AK](https://huggingface.co/papers) paper recommendation alert
- [ ] training a classifier (from [AK](https://huggingface.co/papers) & [ML-Papers-of-the-Week](https://github.com/dair-ai/ML-Papers-of-the-Week)) for recommendations
