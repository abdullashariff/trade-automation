import MetaTrader5 as mt5
import time

# MetaTrader 5 login credentials (replace these with your actual account details)
account_id = 87429762  # Your MetaTrader 5 account ID
password = "7k@pTcCm" #"Alumni27**"  # Your MetaTrader 5 password
server = "MetaQuotes-Demo"  # The server provided by your broker

# display data on the MetaTrader 5 package
print("MetaTrader5 package author: ",mt5.__author__)
print("MetaTrader5 package version: ",mt5.__version__)

# Function to log into your MetaTrader account
def login_to_metatrader(account_id, password, server):
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()

    authorized = mt5.login(account_id, password=password, server=server)
    if authorized:
        print(f"Logged into account #{account_id}")
    else:
        print(f"Failed to log in to account #{account_id}, error code: {mt5.last_error()}")

# Call the login function
login_to_metatrader(account_id, password, server)

# Function to fetch account balance and equity
def get_account_info():
    account_info = mt5.account_info()
    if account_info is not None:
        print(f"Balance: {account_info.balance}, Equity: {account_info.equity}")
    else:
        print("Failed to retrieve account information")

# Function to place a Buy order
def place_buy_order(symbol, lot_size):
    # Check if the symbol is available for trading
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select {symbol}")
        return
    
    # Place a Buy order
    result = mt5.order_send({
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        "sl": 1.0800,  # Example Stop Loss
        "tp": 1.1000,  # Example Take Profit
        "deviation": 20,
        "magic": 234000,
        "comment": "Test Buy Order"
    })

    # Check the result of the trade
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print("Buy order executed successfully")
    else:
        print(f"Failed to execute Buy order: {result.retcode}")
        print("Error:", mt5.last_error())

# Function to monitor open positions
def monitor_positions():
    positions = mt5.positions_get()
    if positions:
        print("Open positions:")
        for position in positions:
            print(f"Position: {position}")
    else:
        print("No open positions")

# Function to close Buy positions
def close_buy_position(symbol):
    for position in mt5.positions_get(symbol=symbol):
        if position.type == mt5.ORDER_TYPE_BUY:
            result = mt5.order_send({
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL,
                "position": position.ticket,
                "price": mt5.symbol_info_tick(symbol).bid,
                "deviation": 20,
                "magic": 234000,
                "comment": "Closing Buy position"
            })

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print("Buy position closed successfully")
            else:
                print(f"Failed to close Buy position: {result.retcode}")
                print("Error:", mt5.last_error())

# Test the functions
symbol = "EURUSD"  # The symbol for the test
lot_size = 0.1  # Define the lot size for the trade

# Fetch account info
get_account_info()

# Place a Buy order
place_buy_order(symbol, lot_size)

# Wait for 5 seconds before checking open positions
time.sleep(5)

# Monitor open positions
monitor_positions()

# Close the Buy position
close_buy_position(symbol)

# Shut down the MetaTrader 5 connection
mt5.shutdown()
