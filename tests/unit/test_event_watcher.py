import os
from unittest.mock import patch
from event_watcher import EventWatcher, DEPOSIT_TOPIC, WITHDRAW_TOPIC, MINIPOOL_CREATED_TOPIC
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
    block_number = 21053646
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

@patch("requests.post")
def test_fetch_logs_success(mock_post):
    """Test that fetch_logs calls Alchemy API with eth_getLogs"""

    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    watcher = EventWatcher(discord_webhook_url)

    # Mock response from Alchemy
    block_number = 21053646
    expected_response =  {
        'address': '0x09fbce43e4021a3f69c4599ff00362b83eda501e',
        'blockHash': '0xc40860b311c3c4922b05723191b071b6a84d5552e66f688af21de51c8d11dd7e',
        'blockNumber': '0x14140ce',
        'data': '0x00000000000000000000000000000000000000000000000000000000671d95c3',
        'logIndex': '0x4',
        'removed': False,
        'topics': [
            '0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4',
            '0x000000000000000000000000fa1afe127509ce04979734e09f6f49b9c2acab18',
            '0x0000000000000000000000002a906f92b0378bb19a3619e2751b1e0b8cab6b29'
        ],
        'transactionHash': '0x7a309de4d4a91769e28372d23eab29b425c65ab5a19396f8ab2eee4f8c6677bc',
        'transactionIndex': '0x1'
    }
    mock_post.return_value.json.return_value = expected_response

    result = watcher.fetch_logs(block_number)

    assert result is not None
    mock_post.assert_called_once_with(
        f'https://eth-mainnet.alchemyapi.io/v2/{os.getenv("ALCHEMY_API_KEY")}',
        json={
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(block_number),
                "toBlock": hex(block_number),
                "topics": [[DEPOSIT_TOPIC, WITHDRAW_TOPIC, MINIPOOL_CREATED_TOPIC]]
            }],
            "id": 1
        }
    )