import os
import requests
import time
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

INTERNAL_DISCORD_WEBHOOK_URL = os.getenv("INTERNAL_DISCORD_WEBHOOK_URL")
ALCHEMY_API_KEY = os.getenv("ALCHEMY_API_KEY")
ORACLE_CONTRACT_ADDRESS = "0x81C1001e1621d05bE250814123CC81BBb244Cb07"

ALCHEMY_URL = f"https://eth-mainnet.alchemyapi.io/v2/{ALCHEMY_API_KEY}"

ORACLE_TIME_THRESHOLD = os.getenv("ORACLE_TIME_THRESHOLD", 24.5)  # Time threshold in hours

class MonitorOracle:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_discord_alert(self, message):
        """Send an alert message to the Discord channel and ping everyone."""
        payload = {
            "content": "@everyone",
            "embeds": [{
                "title": "🔮 Oracle Update Alert",
                "description": message,
            }]
        }
        requests.post(self.webhook_url, json=payload)

    def get_last_updated_timestamp(self):
        """Retrieve the last updated timestamp from the Oracle contract."""
        params = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{
                "to": ORACLE_CONTRACT_ADDRESS,
                "data": "0xb1b4bf65" # function selector for getLastUpdatedTotalYieldAccrued()
            }, "latest"],
            "id": 1
        }

        response = requests.post(ALCHEMY_URL, json=params).json()
        if 'result' in response:
            # Convert hex to int (timestamp)
            last_updated = int(response['result'], 16)
            return last_updated
        else:
            print(f"Error retrieving last updated timestamp: {response}")
            return None

    def run(self):
        """Monitor the Oracle updates and alert if not updated in 24 hours."""
        while True:
            last_updated = self.get_last_updated_timestamp()
            if last_updated is not None:
                # Get current time
                current_time = int(time.time())

                # Calculate time difference in hours
                time_difference = (current_time - last_updated) / 3600  # Convert seconds to hours
                print(f"{time_difference:.2f} hours since last updated.")

                # Check if the last updated time is older than ORACLE_TIME_THRESHOLD
                if time_difference > ORACLE_TIME_THRESHOLD:
                    last_updated_datetime = datetime.fromtimestamp(last_updated, pytz.timezone('America/Los_Angeles'))
                    formatted_timestamp = last_updated_datetime.strftime('%B %d, %Y at %I:%M %p PST')
                    alert_message = (
                        f"The Oracle is out of date."
                        f"\nLast updated at: {formatted_timestamp}"

                    )
                    self.send_discord_alert(alert_message)
            time.sleep(60 * 60)  # Check once every hour

if __name__ == "__main__":
    oracle_monitor = MonitorOracle(INTERNAL_DISCORD_WEBHOOK_URL)
    oracle_monitor.run()
