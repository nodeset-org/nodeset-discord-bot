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
SWAP_TOPIC = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"

SLEEP_TIME = int(os.getenv("SLEEP_TIME", 5))  # Polling interval in seconds

LAST_BLOCK = int(os.getenv("LAST_BLOCK", 21024052))  # Starting block


class EventWatcher:
    def __init__(self, webhook_url, last_block):
        self.webhook_url = webhook_url
        self.last_block = last_block

    def notify_channel(self, title, message):
        """Send a message to the Discord channel."""
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
            }]
        }
        print("Notifying channel:")
        print(payload)
        requests.post(self.webhook_url, json=payload)

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

    def fetch_transaction_receipt(self, tx_hash):
        """Fetch logs for a specific transaction"""
        response = requests.post(
            ALCHEMY_URL,
            json={
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": 1
            }
        ).json()

        receipt = response.get("result")
        if receipt and "logs" in receipt:
            return receipt
        else:
            print(f"No receipt found for transaction {tx_hash}")
            return {}

    def extract_topics_from_logs(self, logs):
        """Extract topics from logs."""
        topics_list = list(set([topic for log in logs for topic in log['topics']]))
        return topics_list


    def check_block_exists(self, block_number):
        """Check if the block exists."""
        block_data = self.get_block_data(block_number)
        if not block_data or block_data.get('error'):
            print(f"Block {block_number} does not exist yet, retrying...")
            return False
        return True


    def process_log(self, log):
        """Process a single log entry."""
        address = log["address"].lower() # Sender address
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

        fetched_receipt = self.fetch_transaction_receipt(log["transactionHash"])
        if not fetched_receipt:
            return
        fetched_logs = fetched_receipt["logs"]
        extracted_topics = self.extract_topics_from_logs(fetched_logs)

        # Ignore if to (contract) address is not supernode account
        if fetched_receipt['to'].lower() not in { SUPERNODE_ACCOUNT_ADDRESS.lower(),WETH_VAULT_ADDRESS.lower(), RPL_VAULT_ADDRESS.lower() }:
            return

        asset_type = "RPL" if fetched_receipt['to'].lower() == RPL_VAULT_ADDRESS.lower() else "ETH"

        if topic == DEPOSIT_TOPIC:
            if SWAP_TOPIC in extracted_topics:
                title =  "**New Deposit (potential arb)**"
            else:
                title = "**New Deposit**"

            message = (f"🚀 Amount: **{assets_value:.2f} {asset_type}**\n"
                       f"📍 Address: [{formatted_address}](http://etherscan.io/address/{formatted_address})\n"
                       f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                       f"🔗 Block Number: {block_number}\n"
                       f"⏰ Time: {relative_timestamp}\n")
            self.notify_channel(title, message)

        elif topic == WITHDRAW_TOPIC:
            if SWAP_TOPIC in extracted_topics:
                title =  "**New Withdrawal (potential arb)**"
            else:
                title =  "**New Withdrawal**"

            message = (f"💸 Amount: **{assets_value:.2f} {asset_type}**\n"
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
        while True:
            print(f"Processing block: {self.last_block}")

            try:
                if not self.check_block_exists(self.last_block):
                    time.sleep(SLEEP_TIME)
                    continue

                logs = self.fetch_logs(self.last_block)
                for log in logs:
                    self.process_log(log)
                # Move to the next block
                self.last_block += 1

            except Exception as e:
                print(f"Error processing block: {e}")
            time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    watcher = EventWatcher(DISCORD_WEBHOOK_URL, LAST_BLOCK)
    watcher.run()