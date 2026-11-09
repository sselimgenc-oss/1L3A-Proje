"""
All-Weather SPS-03 Autonomous Trading & Mark-to-Market Engine
Executes every hour via GitHub Actions (.github/workflows/paper_trader.yml).
Fetches live prices from Binance Public REST API / Yahoo Finance and updates data.json.
"""
import json, os, datetime, urllib.request

DATA_PATH = os.path.join(os.path.dirname(__file__), 'data.json')

def fetch_crypto_price(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return float(data['price'])
    except Exception as e:
        return None

def main():
    if not os.path.exists(DATA_PATH):
        print(f"Error: {DATA_PATH} not found.")
        return

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    time_str = now.strftime("%d/%m %H:%M")
    print(f"Executing Bot Engine at {time_str} (UTC+3)...")

    if 'meta' in data:
        data['meta']['last_update'] = time_str

    crypto_symbols = {'BTC', 'ETH', 'SOL', 'AVAX', 'BNB', 'NEAR', 'DOT', 'DOGE', 'LTC', 'LINK'}
    crypto_prices = {}
    for sym in crypto_symbols:
        p = fetch_crypto_price(sym)
        if p:
            crypto_prices[sym] = p

    total_unrealized = 0.0
    if 'open_positions' in data:
        for pos in data['open_positions']:
            asset = pos.get('asset', '')
            if asset in crypto_prices:
                current_p = crypto_prices[asset]
                entry_p = float(pos.get('entry_price', current_p))
                size = float(pos.get('size_usd', 2000))
                pnl = (current_p - entry_p) / entry_p * size if pos.get('type') == 'Alış' else (entry_p - current_p) / entry_p * size
                pos['unrealized_pnl'] = round(pnl, 2)
                stop_p = float(pos.get('stop_price', entry_p * 0.96))
                risk = abs(entry_p - stop_p) / entry_p * size
                if risk > 0:
                    pos['r'] = round(pnl / risk, 2)
            total_unrealized += pos.get('unrealized_pnl', 0.0)

    print(f"Updated open positions. Total Unrealized: ${total_unrealized:.2f}")

    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("data.json updated successfully.")

if __name__ == '__main__':
    main()
