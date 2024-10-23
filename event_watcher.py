import os
from dotenv import load_dotenv

import discord
import requests
import asyncio

load_dotenv()


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
WETH_VAULT_ADDRESS = "0xBB22d59B73D7a6F3A8a83A214BECc67Eb3b511fE"
RPL_VAULT_ADDRESS = "0x1DB1Afd9552eeB28e2e36597082440598B7F1320"
SUPERNODE_ACCOUNT_ADDRESS = "0x2A906f92B0378Bb19a3619E2751b1e0b8cab6B29"

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

DEPOSIT_TOPIC = "0xdcbc1c05240f31ff3ad067ef1ee35ce4997762752e3a095284754544f4c709d7"
WITHDRAW_TOPIC = "0xfbde797d201c681b91056529119e0b02407c7bb96a4a2c75c01fc9667232c8db"
MINIPOOL_CREATED_TOPIC = "0x08b4b91bafaf992145c5dd7e098dfcdb32f879714c154c651c2758a44c7aeae4"

SLEEP_TIME = int(os.getenv("SLEEP_TIME")) if os.getenv("SLEEP_TIME") else 300  # Polling interval in seconds

intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def notify_channel(message):
    channel = client.get_channel(CHANNEL_ID)
    await channel.send(message)

# Poll for:
# - New deposits and withdrawals from the WETH and RPL vaults
# - New minipools created by supernodes
async def poll_ethereum_events():
    # Start at when Constellation was deployed (-10 blocks to be safe)
    last_block = int(os.getenv("LAST_BLOCK")) if os.getenv("LAST_BLOCK") else 20946645

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

            response = requests.post(ALCHEMY_URL, json=params).json()
            logs = response.get("result", [])

            for log in logs:
                address = log["address"].lower()
                topic = log["topics"][0]
                block_number = int(log["blockNumber"], 16)  # Convert block number from hex to int
                transaction_hash = log["transactionHash"]

                # Only handle logs from relevant addresses
                if address not in {WETH_VAULT_ADDRESS.lower(), RPL_VAULT_ADDRESS.lower(), SUPERNODE_ACCOUNT_ADDRESS.lower()}:
                    continue

                event_data = log["data"]
                raw_assets = int(event_data[2:66], 16)  # First 32 bytes for assets
                # raw_shares = int(event_data[66:], 16)   # Next 32 bytes for shares

                assets_value = raw_assets / 10**18
                # shares_value = raw_shares / 10**18

                asset_type = "ETH" if address == WETH_VAULT_ADDRESS.lower() else "RPL"

                # Notify discord channel
                if topic == DEPOSIT_TOPIC:
                    message = (
                        f"🚀 **New Deposit** of {assets_value:.18f} {asset_type} at {address}\n"
                        f"📦 Transaction Hash: {transaction_hash}\n"
                        f"🔗 Block Number: {block_number}"
                    )
                    await notify_channel(message)

                elif topic == WITHDRAW_TOPIC:
                    message = (
                        f"💸 **New Withdrawal** of {assets_value:.18f} {asset_type} from {address}\n"
                        f"📦 Transaction Hash: {transaction_hash}\n"
                        f"🔗 Block Number: {block_number}\n"
                    )
                    await notify_channel(message)

                elif topic == MINIPOOL_CREATED_TOPIC:
                    minipool_address = f"0x{log['topics'][1][26:]}"
                    message = (
                        f"🎉 **New Minipool Created** at {minipool_address}\n"
                        f"📦 Transaction Hash: {transaction_hash}\n"
                        f"🔗 Block Number: {block_number}"
                    )
                    await notify_channel(message)

            # Move to the next block
            last_block += 1

        except Exception as e:
            print(f"Error fetching logs: {e}")

        await asyncio.sleep(SLEEP_TIME)



@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(poll_ethereum_events())  # Start polling the Ethereum events


# Run the bot
client.run(DISCORD_TOKEN)