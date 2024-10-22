import discord
import requests
import asyncio
from dotenv import load_dotenv
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
WETH_VAULT_ADDRESS = "0xBB22d59B73D7a6F3A8a83A214BECc67Eb3b511fE"
RPL_VAULT_ADDRESS = "0x1DB1Afd9552eeB28e2e36597082440598B7F1320"
SUPERNODE_ACCOUNT_ADDRESS = "0x2A906f92B0378Bb19a3619E2751b1e0b8cab6B29"

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

# keccak256("Deposit(address,uint256)")
DEPOSIT_TOPIC = "0x8c5be1e5ebec7d5bd14f714f9d784a1fa9c76d55758c7cbf4a1e57ed0fd38b34"

# keccak256("Withdraw(address,uint256)")
WITHDRAW_TOPIC = "0x00fdd58e5e76e60bc2fae8d739b8f85ed4b50a1f1ca20e8b31f7efb278df1f8d"

# keccak256("MinipoolCreated(address,address)")
MINIPOOL_CREATED_TOPIC = "0xe2f07ab4919f5ad3fa170fa21acff1d9bca6633df6b22b5c4a6f0acfbef72d19"

SLEEP_TIME = 300 # 5 minutes

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
    last_block = 20946655 - 10

    while True:
        try:
            # If this is the first run, get the latest block number
            if last_block is None:
                response = requests.get(f"{ALCHEMY_URL}?jsonrpc=2.0&method=eth_blockNumber&params=[]&id=1").json()
                last_block = int(response["result"], 16)
            params = {
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [{
                    "fromBlock": hex(last_block),
                    "toBlock": "latest",
                    "address": [WETH_VAULT_ADDRESS, RPL_VAULT_ADDRESS, SUPERNODE_ACCOUNT_ADDRESS],
                    "topics": [[DEPOSIT_TOPIC, WITHDRAW_TOPIC, MINIPOOL_CREATED_TOPIC]]
                }],
                "id": 1
            }

            response = requests.post(ALCHEMY_URL, json=params).json()

            # Process event logs
            logs = response.get("result", [])
            for log in logs:
                topic = log["topics"][0]
                address = log["address"]
                event_data = int(log["data"], 16)

                asset_type = "ETH" if address == WETH_VAULT_ADDRESS else "RPL"

                # Notify discord channel
                if topic == DEPOSIT_TOPIC:
                    message = f"🚀 **New Deposit** of {event_data} {asset_type} at {address}"
                    await notify_channel(message)
                elif topic == WITHDRAW_TOPIC:
                    message = f"💸 **New Withdrawal** of {event_data} {asset_type} from {address}"
                    await notify_channel(message)
                elif topic == MINIPOOL_CREATED_TOPIC:
                    minipool_address = f"0x{log['topics'][1][26:]}"
                    message = f"🎉 **New Minipool Created** at {minipool_address}"
                    await notify_channel(message)

            latest_block = requests.get(f"{ALCHEMY_URL}?jsonrpc=2.0&method=eth_blockNumber&params=[]&id=1").json()
            last_block = int(latest_block["result"], 16) + 1

        except Exception as e:
            print(f"Error fetching logs: {e}")

        # Wait x minutes/seconds before polling again to avoid hitting rate limits
        await asyncio.sleep(SLEEP_TIME)


@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(poll_ethereum_events())  # Start polling the Ethereum events


# Run the bot
client.run(DISCORD_TOKEN)