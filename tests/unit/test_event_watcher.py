import os
from unittest.mock import patch
from event_watcher import notify_channel
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env.test')

@patch("requests.post")
def test_notify_channel(mock_post):
    """Test the notify_channel function to ensure it sends the correct payload to the webhook."""

    message_title = "Test Title"
    message_body = "This is a test message."

    notify_channel(message_title, message_body)

    mock_post.assert_called_once()

    # Check the data sent to the webhook
    expected_payload = {
        "embeds": [{
            "title": message_title,
            "description": message_body,
        }]
    }
    mock_post.assert_called_with(os.getenv("DISCORD_WEBHOOK_URL"), json=expected_payload)

