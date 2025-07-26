def calculate_position_size(usdt_balance, risk_percent, leverage, entry_price):
    risk_amount = usdt_balance * (risk_percent / 100)
    position_value = risk_amount * leverage
    amount = position_value / entry_price
    return round(amount, 6)
