import os
import pytest
import requests
from unittest.mock import patch
from event_watcher import notify_channel  # Adjust the import based on your directory structure

@pytest.mark.asyncio
async def test_notify_channel():
    webhook_url = "https://example.com/webhook"  # Your test webhook URL
    os.environ["DISCORD_WEBHOOK_URL"] = webhook_url

    message_title = "Test Title"
    message_body = "This is a test message."

    with patch("requests.post") as mock_post:
        await notify_channel(message_title, message_body)

        # Check that the post method was called once
        mock_post.assert_called_once()

        # Check the data sent to the webhook
        expected_payload = {
            "embeds": [{
                "title": message_title,
                "description": message_body,
            }]
        }
        # Assert that the correct payload was sent
        mock_post.assert_called_with(webhook_url, json=expected_payload)
