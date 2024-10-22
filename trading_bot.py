import MetaTrader5 as mt5
import pandas as pd
import numpy as np
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
        mt5.shutdown()
        quit()

    print("initialize successfull")

    authorized = mt5.login(account_id, password=password, server=server)
    if authorized:
        print(f"Logged into account #{account_id}")
    else:
        print(f"Failed to log in to account #{account_id}, error code: {mt5.last_error()}")

# Call the login function
login_to_metatrader(account_id, password, server)

# Trading parameters
symbol = "EURUSD"
lot_size = 0.1
risk_percentage = 0.03  # Risk 3% of account balance per trade
standard_stop_loss_percentage = 0.10  # 10% stop loss
take_profit_ratio = 2  # Risk-to-reward ratio of 1:2
volatility_threshold_high = 0.02  # High volatility threshold
volatility_threshold_moderate = 0.01  # Moderate volatility threshold
trailing_stop_percentage = 0.05  # Trailing stop is 5% away from current price

# Drawdown management
max_balance = 0
drawdown_limit = 0.10  # 10% drawdown limit

# Function to fetch real-time market data
def fetch_real_time_data(symbol):
    prices = mt5.symbol_info_tick(symbol)
    return prices.ask, prices.bid

# Function to calculate technical indicators
def calculate_indicators(symbol):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1000)  # Get 1000 hourly candles
    df = pd.DataFrame(rates)
    df['MA_50'] = df['close'].rolling(window=50).mean()
    df['MA_200'] = df['close'].rolling(window=200).mean()
    df['RSI'] = calculate_rsi(df['close'], 14)  # Calculate RSI
    df['MACD'], df['MACD_signal'] = calculate_macd(df['close'])  # Calculate MACD
    df['Upper_BB'], df['Lower_BB'] = calculate_bollinger_bands(df['close'])  # Calculate Bollinger Bands
    df['ATR'] = calculate_atr(df['close'], 14)  # Calculate ATR for volatility
    return df

# Function to calculate RSI
def calculate_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Function to calculate MACD
def calculate_macd(series, fast_period=12, slow_period=26, signal_period=9):
    exp1 = series.ewm(span=fast_period, adjust=False).mean()
    exp2 = series.ewm(span=slow_period, adjust=False).mean()
    macd = exp1 - exp2
    macd_signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, macd_signal

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(series, window=20, num_sd=2):
    rolling_mean = series.rolling(window=window).mean()
    rolling_std = series.rolling(window=window).std()
    upper_band = rolling_mean + (rolling_std * num_sd)
    lower_band = rolling_mean - (rolling_std * num_sd)
    return upper_band, lower_band

# Function to calculate Average True Range (ATR)
def calculate_atr(close_prices, period):
    high_low = close_prices.rolling(window=period).max() - close_prices.rolling(window=period).min()
    high_prev_close = np.abs(close_prices.rolling(window=period).max() - close_prices.shift(1))
    low_prev_close = np.abs(close_prices.rolling(window=period).min() - close_prices.shift(1))
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    return true_range.rolling(window=period).mean()

# Function to determine leverage based on market volatility
def determine_leverage(atr):
    if atr > volatility_threshold_high:
        return 10  # Low leverage for high volatility
    elif atr > volatility_threshold_moderate:
        return 25  # Moderate leverage for moderate volatility
    else:
        return 50  # High leverage for low volatility (sideways market)

# Function to place a market order with risk management and leverage adjustments
def place_order(symbol, action, lot_size):
    global max_balance  # Access the global variable for max balance
    account_info = mt5.account_info()
    if account_info is None:
        print("Failed to get account info")
        return
    
    # Calculate the maximum risk amount
    account_balance = account_info.balance
    risk_amount = account_balance * risk_percentage
    
    # Check for drawdown limit
    if account_balance < max_balance * (1 - drawdown_limit):
        print("Drawdown limit reached. Halting trading.")
        return
    
    # Fetch current prices
    price = mt5.symbol_info_tick(symbol).ask if action == "buy" else mt5.symbol_info_tick(symbol).bid
    
    # Calculate stop loss and take profit
    df = calculate_indicators(symbol)
    atr = df['ATR'].iloc[-1]  # Get the latest ATR value
    leverage = determine_leverage(atr)  # Adjust leverage based on volatility

    stop_loss = price * (1 - standard_stop_loss_percentage) if action == "buy" else price * (1 + standard_stop_loss_percentage)
    take_profit = price + (price - stop_loss) * take_profit_ratio if action == "buy" else price - (stop_loss - price) * take_profit_ratio
    
    # Calculate position size based on risk and leverage
    position_size = (risk_amount / (standard_stop_loss_percentage * price)) * leverage
    position_size = min(position_size, lot_size)  # Ensure we don't exceed lot size
    
    # Create a buy/sell request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position_size,
        "type": mt5.ORDER_BUY if action == "buy" else mt5.ORDER_SELL,
        "price": price,
        "sl": stop_loss,
        "tp": take_profit,
        "deviation": 10,
        "magic": 234000,
        "comment": "Python Script Trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    # Send the order
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode}")
    else:
        max_balance = max(max_balance, account_balance)  # Update max balance if current balance exceeds it
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            # Start trailing stop loss
            trailing_stop_loss(symbol, result.order)
    return result

# Function to implement trailing stop loss
def trailing_stop_loss(symbol, order_ticket):
    while True:
        time.sleep(60)  # Check every minute
        order_info = mt5.order_get(ticket=order_ticket)
        if order_info is None:
            print("Order not found.")
            break
        
        current_price = mt5.symbol_info_tick(symbol).ask if order_info.type == mt5.ORDER_BUY else mt5.symbol_info_tick(symbol).bid
        new_sl = None
        
        # Adjust stop loss for buy orders
        if order_info.type == mt5.ORDER_BUY:
            new_sl = current_price * (1 - trailing_stop_percentage)  # Set trailing stop at 5% below current price
            if new_sl > order_info.sl:  # Update SL only if the new SL is higher
                mt5.order_modify(order_ticket, price=order_info.price, sl=new_sl, tp=order_info.tp, deviation=10)
                print(f"Updated trailing stop loss for BUY order: {new_sl}")

        # Adjust stop loss for sell orders
        elif order_info.type == mt5.ORDER_SELL:
            new_sl = current_price * (1 + trailing_stop_percentage)  # Set trailing stop at 5% above current price
            if new_sl < order_info.sl:  # Update SL only if the new SL is lower
                mt5.order_modify(order_ticket, price=order_info.price, sl=new_sl, tp=order_info.tp, deviation=10)
                print(f"Updated trailing stop loss for SELL order: {new_sl}")

# Example trading strategy with multiple indicators and leverage adjustments
def trading_strategy():
    while True:
        ask, bid = fetch_real_time_data(symbol)
        df = calculate_indicators(symbol)

        latest_data = df.iloc[-1]

        # Check if market conditions are favorable for trading
        if (latest_data['MA_50'] > latest_data['MA_200'] and 
            latest_data['RSI'] < 70 and 
            latest_data['MACD'] > latest_data['MACD_signal'] and 
            bid < latest_data['Lower_BB']):
            print(f"Placing Buy Order for {symbol}")
            result = place_order(symbol, "buy", lot_size)
            print(result)

        elif (latest_data['MA_50'] < latest_data['MA_200'] and 
              latest_data['RSI'] > 30 and 
              latest_data['MACD'] < latest_data['MACD_signal'] and 
              ask > latest_data['Upper_BB']):
            print(f"Placing Sell Order for {symbol}")
            result = place_order(symbol, "sell", lot_size)
            print(result)

        # Wait for a specific interval before checking again
        time.sleep(300)  # Wait for 5 minutes

# Run the trading strategy
trading_strategy()

# Shutdown MetaTrader 5 when done
mt5.shutdown()

