# nodeset-discord-bot
Discord bot for displaying NodeSet-related events

## Notes

The instruction set is based on Python 3+. If you're using 2, modify the commands to `pip` and `python`.

## Installation

Depending on your environment:

```
pip3 install -r requirements.txt
```

## Running the Bot Locally

1. Create a .env file with all the keys/tokens filled in

```
cp .env.default .env
```

2. Run the bot

```
python3 event_watcher.py
```

## Running tests

```
python3 -m pytest tests/
```