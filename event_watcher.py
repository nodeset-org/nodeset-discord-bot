import os
from dotenv import load_dotenv

import requests
import time

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

WETH_VAULT_ADDRESS = "0xBB22d59B73D7a6F3A8a83A214BECc67Eb3b511fE"
RPL_VAULT_ADDRESS = "0x1DB1Afd9552eeB28e2e36597082440598B7F1320"
SUPERNODE_ACCOUNT_ADDRESS = "0x2A906f92B0378Bb19a3619E2751b1e0b8cab6B29"

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

DEPOSIT_TOPIC = "0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7"
WITHDRAW_TOPIC = "0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db"
MINIPOOL_CREATED_TOPIC = "0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4"

SLEEP_TIME = int(os.getenv("SLEEP_TIME", 5))  # Polling interval in seconds

last_block = int(os.getenv("LAST_BLOCK", 21024052))  # Starting block


class EventWatcher:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def notify_channel(self, title, message):
        """Send a message to the Discord channel."""
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
            }]
        }
        requests.post(DISCORD_WEBHOOK_URL, json=payload)

    def get_block_data(self, block_number):
        """Get block data from the blockchain via Alchemy."""
        response = requests.post(
            ALCHEMY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getBlockByNumber",
                "params": [hex(block_number), False],
                "id": 1
            }
        ).json()
        return response.get("result")

    def fetch_logs(self, block):
        """Fetch logs for a specific block."""
        params = {
            "jsonrpc": "2.0",
            "method": "eth_getLogs",
            "params": [{
                "fromBlock": hex(block),
                "toBlock": hex(block),
                "topics": [[DEPOSIT_TOPIC, WITHDRAW_TOPIC, MINIPOOL_CREATED_TOPIC]]
            }],
            "id": 1
        }
        response = requests.post(ALCHEMY_URL, json=params).json()
        return response.get("result", [])


    def process_log(self, log):
        """Process a single log entry."""
        print(f"Processing log: {log}")
        address = log["address"].lower()
        topic = log["topics"][0]
        block_number = int(log["blockNumber"], 16)
        transaction_hash = log["transactionHash"]

        block_data = self.get_block_data(block_number)
        if not block_data:
            print(f"Could not retrieve block data for block number: {block_number}")
            return

        timestamp = int(block_data["timestamp"], 16)
        relative_timestamp = f"<t:{timestamp}:R>"

        if topic in {DEPOSIT_TOPIC, WITHDRAW_TOPIC} and address not in {WETH_VAULT_ADDRESS.lower(), RPL_VAULT_ADDRESS.lower()}:
            return  # Ignore irrelevant logs

        event_data = log["data"]
        raw_assets = int(event_data[2:66], 16)  # First 32 bytes for assets
        assets_value = raw_assets / 10**18

        formatted_address = f"0x{int(log['topics'][1], 16):040x}"  # Sender address

        if topic == DEPOSIT_TOPIC:
            title =  f"**New Deposit**"
            message = (f"🚀 Amount: **{assets_value:.2f}**\n"
                       f"📍 Address: [{formatted_address}](http://etherscan.io/address/{formatted_address})\n"
                       f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                       f"🔗 Block Number: {block_number}\n"
                       f"⏰ Time: {relative_timestamp}\n")
            self.notify_channel(title, message)

        elif topic == WITHDRAW_TOPIC:
            title = f"**New Withdrawal**"
            message = (f"💸 Amount: **{assets_value:.2f}**\n"
                       f"📍 Address: [{formatted_address}](http://etherscan.io/address/{formatted_address})\n"
                       f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                       f"🔗 Block Number: {block_number}\n"
                       f"⏰ Time: {relative_timestamp}\n")
            self.notify_channel(title, message)

        elif topic == MINIPOOL_CREATED_TOPIC:
            minipool_address = f"0x{log['topics'][1][26:]}"
            title = f"**New Minipool**"
            message = (f"🌊 Minipool Address: [{minipool_address}](http://etherscan.io/address/{minipool_address})\n"
                       f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                       f"🔗 Block Number: {block_number}\n"
                       f"⏰ Time: {relative_timestamp}\n")
            self.notify_channel(title, message)


    def run(self):
        """Start the process for monitoring and processing events to Discord."""
        global last_block

        while True:
            print(f"Processing block: {last_block}")

            try:
                logs = self.fetch_logs(last_block)
                for log in logs:
                    self.process_log(log)
                # Move to the next block
                last_block += 1

            except Exception as e:
                print(f"Error processing block: {e}")
            time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    watcher = EventWatcher(DISCORD_WEBHOOK_URL)
    watcher.run()