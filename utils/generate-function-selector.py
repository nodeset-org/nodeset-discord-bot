from web3 import Web3

# Define the function signature
function_signature = "getLastUpdatedTotalYieldAccrued()"

# Calculate the keccak256 hash and take the first 4 bytes
function_selector = Web3.keccak(text=function_signature)[:4].hex()

print(function_selector)