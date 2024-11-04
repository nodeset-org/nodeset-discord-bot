import os
from unittest.mock import patch
from event_watcher import EventWatcher
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.test')

@patch("requests.post")
def test_notify_channel_success(mock_post):
    """Test the notify_channel function to ensure it sends the correct payload to the webhook."""

    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    watcher = EventWatcher(discord_webhook_url)

    message_title = "Some random title"
    message_body = "Some random message"

    watcher.notify_channel(message_title, message_body)

    mock_post.assert_called_once()

    # Check the data sent to the webhook
    expected_payload = {
        "embeds": [{
            "title": message_title,
            "description": message_body,
        }]
    }
    mock_post.assert_called_with(discord_webhook_url, json=expected_payload)

@patch("requests.post")
def test_get_block_data_success(mock_post):
    """Test that get_block_data calls Alchemy API with eth_getBlockByNumber"""

    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    watcher = EventWatcher(discord_webhook_url)

    # Mock response from Alchemy
    block_number = 21024052
    expected_response = {
        "result": {
            "timestamp": hex(1617980800),  # fake timestamp
        }
    }

    mock_post.return_value.json.return_value = expected_response

    result = watcher.get_block_data(block_number)

    assert result is not None
    assert result["timestamp"] == hex(1617980800)
    mock_post.assert_called_once_with(
        f'https://eth-mainnet.alchemyapi.io/v2/{os.getenv("ALCHEMY_API_KEY")}',
        json={
            "jsonrpc": "2.0",
            "method": "eth_getBlockByNumber",
            "params": [hex(block_number), False],
            "id": 1
        }
    )