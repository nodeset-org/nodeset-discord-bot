import os
from dotenv import load_dotenv

import requests
import asyncio

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")

WETH_VAULT_ADDRESS = "0xBB22d59B73D7a6F3A8a83A214BECc67Eb3b511fE"
RPL_VAULT_ADDRESS = "0x1DB1Afd9552eeB28e2e36597082440598B7F1320"
# SUPERNODE_ACCOUNT_ADDRESS = "0x2A906f92B0378Bb19a3619E2751b1e0b8cab6B29"

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

DEPOSIT_TOPIC = "0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7"
WITHDRAW_TOPIC = "0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db"
MINIPOOL_CREATED_TOPIC = "0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4"

SLEEP_TIME = int(os.getenv("SLEEP_TIME", 5))  # Polling interval in seconds

last_block = int(os.getenv("LAST_BLOCK", 21024052))  # Starting block


async def notify_channel(title, message):
    payload = {
        "embeds":[{
            "title": title,
            "description": message,
        }]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)


# Poll for:
# - New deposits and withdrawals from the WETH and RPL vaults
# - New minipools created by supernodes
async def poll_ethereum_events():
    global last_block

    while True:
        print(f"Processing block: {last_block}")

        try:
            params = {
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": hex(last_block),
                    "toBlock": hex(last_block),
                    "topics": [[DEPOSIT_TOPIC, WITHDRAW_TOPIC, MINIPOOL_CREATED_TOPIC]]
                }],
                "id": 1
            }

            # Block doesn't exist yet so just print error and retry
            response = requests.post(ALCHEMY_URL, json=params).json()
            if 'result' not in response:
                print(f"Unexpected response format: {response}")
                await asyncio.sleep(SLEEP_TIME)
                continue

            logs = response.get("result", [])
            for log in logs:
                address = log["address"].lower()
                topic = log["topics"][0]
                block_number = int(log["blockNumber"], 16)  # Convert block number from hex to int
                transaction_hash = log["transactionHash"]

                block_response = requests.post(
                    ALCHEMY_URL,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getBlockByNumber",
                        "params": [hex(block_number), False],
                        "id": 1
                    }
                ).json()
                block_data = block_response.get("result")

                if block_data:
                    timestamp_hex = block_data["timestamp"]
                    timestamp = int(timestamp_hex, 16)  # Convert hex timestamp to int
                    # Discord's Relative Timestamp format: <t:TIMESTAMP:R>
                    relative_timestamp = f"<t:{timestamp}:R>"
                else:
                    print(f"Could not retrieve block data for block number: {block_number}")
                    continue  # Skip this log if block data is unavailable


                # Only handle logs from relevant addresses for transfers
                if topic in {DEPOSIT_TOPIC, WITHDRAW_TOPIC} and address not in {WETH_VAULT_ADDRESS.lower(), RPL_VAULT_ADDRESS.lower()}:
                    continue

                event_data = log["data"]
                raw_assets = int(event_data[2:66], 16)  # First 32 bytes for assets
                # raw_shares = int(event_data[66:], 16)   # Next 32 bytes for shares

                assets_value = raw_assets / 10**18
                # shares_value = raw_shares / 10**18

                asset_type = "ETH" if address == WETH_VAULT_ADDRESS.lower() else "RPL"
                # Notify discord channel
                if topic == DEPOSIT_TOPIC:
                    title =  f"**New Deposit**"
                    message = (
                        f"🚀 Amount: **{assets_value:.2f} {asset_type}**\n"
                        f"📍 Address: [{address}](http://etherscan.io/address/{address})\n"
                        f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                        f"🔗 Block Number: {block_number}\n"
                        f"⏰ Time: {relative_timestamp}\n"
                    )
                    await notify_channel(title, message)

                elif topic == WITHDRAW_TOPIC:
                    title = f"**New Withdrawal**"
                    message = (
                        f"💸 Amount: **{assets_value:.2f} {asset_type}**\n"
                        f"📍 Address: [{address}](http://etherscan.io/address/{address})\n"
                        f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                        f"🔗 Block Number: {block_number}\n"
                        f"⏰ Time: {relative_timestamp}\n"
                    )
                    await notify_channel(title, message)

                elif topic == MINIPOOL_CREATED_TOPIC:
                    minipool_address = f"0x{log['topics'][1][26:]}"
                    title = f"**New Minipool**\n"
                    message = (
                        f"🌊 Minipool Address: [{minipool_address}](http://etherscan.io/address/{minipool_address})\n"
                        # f"📍 Address: [{address}](http://etherscan.io/address/{address})\n"
                        f"📦 Transaction Hash: [{transaction_hash}](https://etherscan.io/tx/{transaction_hash})\n"
                        f"🔗 Block Number: {block_number}\n"
                        f"⏰ Time: {relative_timestamp}\n"
                    )
                    await notify_channel(title, message)

            # Move to the next block
            last_block += 1

        except Exception as e:
            print(f"Error fetching logs: {e}")

        await asyncio.sleep(SLEEP_TIME)

if __name__ == "__main__":
    asyncio.run(poll_ethereum_events())