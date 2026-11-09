"""freqtrade'i çevrimdışı çalıştırır: borsa piyasa listesini sentetik olarak verir."""
import sys, json
import ccxt, ccxt.async_support as ccxta
PAIRS = "AAVE ADA APT ARB ATOM AVAX BCH BNB BTC DOGE DOT ETC ETH FIL INJ LINK LTC NEAR OP SOL SUI TRX UNI XLM XRP ALGO AXS COMP CRV DASH EGLD EOS FTT ICP LUNA MANA MATIC SAND SRM THETA VET WAVES XMR XTZ ZEC".split()
def mk(b):
    return {"id": b + "USDT", "symbol": f"{b}/USDT:USDT", "base": b, "quote": "USDT", "settle": "USDT",
            "baseId": b, "quoteId": "USDT", "settleId": "USDT", "type": "swap", "spot": False, "margin": False,
            "swap": True, "future": False, "option": False, "index": None, "active": True, "contract": True, "linear": True,
            "inverse": False, "subType": "linear", "contractSize": 1.0, "expiry": None, "expiryDatetime": None, "strike": None,
            "optionType": None, "taker": 0.0005, "maker": 0.0002, "percentage": True, "tierBased": False, "feeSide": "get",
            "precision": {"amount": 1e-8, "price": 1e-8, "cost": None, "base": None, "quote": None},
            "limits": {"leverage": {"min": 1, "max": 20}, "amount": {"min": 1e-8, "max": None},
                       "price": {"min": None, "max": None}, "cost": {"min": 5, "max": None}, "market": {"min": None, "max": None}},
            "marginModes": {"cross": True, "isolated": True}, "created": None, "info": {}}
MARKETS = [mk(b) for b in PAIRS]
async def _alm(self, reload=False, params={}):
    self.set_markets(MARKETS); return self.markets
def _lm(self, reload=False, params={}):
    self.set_markets(MARKETS); return self.markets
ccxta.binance.load_markets = _alm
ccxt.binance.load_markets = _lm
from freqtrade.exchange.binance import Binance
_olt = Binance.load_leverage_tiers
def _lt(self):
    t = _olt(self)
    ref = t.get("BTC/USDT:USDT")
    for b in PAIRS:
        t.setdefault(f"{b}/USDT:USDT", ref)
    return t
Binance.load_leverage_tiers = _lt
from freqtrade.main import main
sys.exit(main(sys.argv[1:]))
