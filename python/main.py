from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import os

# Node access params
RPC_URL = "http://alice:password@127.0.0.1:18443"

def main():
    try:
        # General client for non-wallet-specific commands
        client = AuthServiceProxy(RPC_URL)

        # Get blockchain info
        blockchain_info = client.getblockchaininfo()
        print("Blockchain Info:", blockchain_info)

        miner_wallet = "Miner"
        trader_wallet = "Trader"

        # Create/Load Miner wallet
        try:
            client.createwallet(miner_wallet)
            print(f"Created {miner_wallet} wallet")
        except JSONRPCException as e:
            if any(x in str(e) for x in ["already taken", "already exists", "already loaded"]):
                client.loadwallet(miner_wallet)
                print(f"Loaded {miner_wallet} wallet")
            else:
                raise

        # Create/Load Trader wallet
        try:
            client.createwallet(trader_wallet)
            print(f"Created {trader_wallet} wallet")
        except JSONRPCException as e:
            if any(x in str(e) for x in ["already taken", "already exists", "already loaded"]):
                client.loadwallet(trader_wallet)
                print(f"Loaded {trader_wallet} wallet")
            else:
                raise

        miner_client = AuthServiceProxy(f"{RPC_URL}/wallet/{miner_wallet}")
        trader_client = AuthServiceProxy(f"{RPC_URL}/wallet/{trader_wallet}")

        # Generate mining address with label
        mining_address = miner_client.getnewaddress("Mining Reward")
        print(f"Mining address: {mining_address}")

        # Mine until positive balance (coinbase maturity = 100 blocks)
        # Short comment:
        # Wallet balance for block rewards is initially zero because coinbase transactions
        # require 100 confirmations (maturity rule) before they become spendable.
        print("Comment: Coinbase rewards require 100 confirmations to mature before they appear in wallet balance.")
        
        balance = miner_client.getbalance()
        while balance <= 0:
            miner_client.generatetoaddress(101, mining_address)  # Efficient: mine all at once
            balance = miner_client.getbalance()
            print(f"Mined blocks. Miner balance: {balance}")

        print("Miner wallet balance:", balance)

        # Trader receiving address
        trader_address = trader_client.getnewaddress("Received")
        print(f"Trader receiving address: {trader_address}")

        # Send 20 BTC
        txid = miner_client.sendtoaddress(trader_address, 20)
        print(f"Transaction sent. TxID: {txid}")

        # Check mempool
        mempool_entry = client.getmempoolentry(txid)
        print("Mempool entry:", mempool_entry)

        # Mine 1 block to confirm
        miner_client.generatetoaddress(1, mining_address)
        print("Transaction confirmed with 1 block.")

        # Extract details
        tx = client.getrawtransaction(txid, True)
        block_hash = client.getbestblockhash()
        block = client.getblock(block_hash)
        block_height = block['height']

        # Input (Miner)
        vin = tx['vin'][0]
        input_tx = client.getrawtransaction(vin['txid'], True)
        input_vout = input_tx['vout'][vin['vout']]
        miner_input_amount = input_vout['value']
        miner_input_address = input_vout['scriptPubKey'].get('address') or 'N/A'

        # Outputs
        trader_out = next((o for o in tx['vout'] if abs(o['value'] - 20) < 0.0001), None)
        change_out = next((o for o in tx['vout'] if abs(o['value'] - 20) >= 0.0001), None)

        trader_output_address = trader_out['scriptPubKey'].get('address', 'N/A') if trader_out else 'N/A'
        trader_output_amount = trader_out['value'] if trader_out else 0
        change_address = change_out['scriptPubKey'].get('address', 'N/A') if change_out else 'N/A'
        change_amount = change_out['value'] if change_out else 0
        fees = miner_input_amount - trader_output_amount - change_amount

        # Write to ../out.txt (relative to python/main.py → repo root)
        out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out.txt")
        with open(out_path, 'w') as f:
            f.write(f"{txid}\n")
            f.write(f"{miner_input_address}\n")
            f.write(f"{miner_input_amount}\n")
            f.write(f"{trader_output_address}\n")
            f.write(f"{trader_output_amount}\n")
            f.write(f"{change_address}\n")
            f.write(f"{change_amount}\n")
            f.write(f"{fees}\n")
            f.write(f"{block_height}\n")
            f.write(f"{block_hash}\n")

        print("Successfully wrote out.txt")

    except Exception as e:
        print("Error occurred:", e)

if __name__ == "__main__":
    main()