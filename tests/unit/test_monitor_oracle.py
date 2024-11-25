import os
from unittest.mock import patch
from scripts.monitor_oracle import MonitorOracle, ORACLE_CONTRACT_ADDRESS, ALCHEMY_URL
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.test')

@patch("requests.post")
def test_send_discord_alert_success(mock_post):
    """Test the send_discord_alert function to ensure it sends the correct payload to the webhook."""

    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    watcher = MonitorOracle(discord_webhook_url)

    message_body = "Some random message"

    watcher.send_discord_alert(message_body)

    mock_post.assert_called_once()

    # Check the data sent to the webhook
    expected_payload = {
        "content": "@everyone",
        "embeds": [{
            "title": "🔮 Oracle Update Alert",
            "description": message_body,
        }]
    }
    mock_post.assert_called_with(discord_webhook_url, json=expected_payload)

@patch("requests.post")
def test_get_last_updated_timestamp_success(mock_post):
    """Test that get_last_updated_timestamp calls Alchemy API with eth_call"""
    mock_response = {
        'jsonrpc': '2.0',
        'id': 1,
        'result': '0x5f5e100'  # 1609459200
    }

    # Set up the mock to return the sample response
    mock_post.return_value.json.return_value = mock_response

    # Initialize the monitor
    watcher = MonitorOracle(os.getenv("DISCORD_WEBHOOK_URL"))

    # Call the method
    timestamp = watcher.get_last_updated_timestamp()

    # Verify that the eth_call was made correctly
    expected_params = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [{
            "to": ORACLE_CONTRACT_ADDRESS,
            "data": "0xb1b4bf65"
        }, "latest"],
        "id": 1
    }
    mock_post.assert_called_with(ALCHEMY_URL, json=expected_params)

    # Verify the result
    expected_timestamp = int(mock_response['result'], 16)
    assert timestamp == expected_timestamp