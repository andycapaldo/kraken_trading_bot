import os
from dotenv import load_dotenv
import requests
import time
import hashlib
import hmac
import base64

import urllib

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

def get_current_price(pair):
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200 and 'result' in data:
        last_trade_price = float(data['result'][pair]['c'][0])
        return last_trade_price
    else:
        print("Error fetching price data:", data)
        return None


def kraken_request(uri_path, data, api_key, api_secret):
    url = "https://api.kraken.com" + uri_path
    headers = {
        'API-Key': api_key,
        'API-Sign': get_kraken_signature(uri_path, data, api_secret)
    }
    response = requests.post(url, headers=headers, data=data)
    return response.json()


def get_kraken_signature(urlpath, data, secret):
    postdata = urllib.parse.urlencode(data)
    message = urlpath.encode() + hashlib.sha256((data['nonce'] + postdata).encode()).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    return base64.b64encode(mac.digest())

def need_to_place_order():
    data = {'nonce': str(int(1000 * time.time()))}
    response = kraken_request('/0/private/BalanceEx', data, api_key, api_secret)
    
    if response and 'result' in response:
        usdc_balance = float(response['result']['USDC']['balance'])
        usdc_held = float(response['result']['USDC']['hold_trade'])
        cad_balance = float(response['result']['ZCAD']['balance'])
        cad_held = float(response['result']['ZCAD']['hold_trade'])
        
        if usdc_balance > usdc_held:
            return {"Place Trade": True, "Type": "USDC", "Volume": usdc_balance}
        elif (cad_balance > cad_held):
            return {"Place Trade": True, "Type": "ZCAD", "Volume": cad_balance}
        else:
            return {"Place Trade": False}
    else:
        print("Error fetching balance:", response)
        return False

def place_stop_loss_order(pair, volume):
    price = 1.3865
    volume = volume / price
    data = {
        'nonce': str(int(1000 * time.time())),
        'ordertype': 'stop-loss',
        'type': 'sell',
        'volume': volume,
        'pair': pair,
        'price': str(price),
    }
    response = kraken_request('/0/private/AddOrder', data, api_key, api_secret)
    return response

def place_take_profit_order(pair, volume):
    price = 1.3415
    volume = volume / price
    print(volume)
    data = {
        'nonce': str(int(1000 * time.time())),
        'ordertype': 'take-profit',
        'type': 'buy',
        'volume': volume,
        'pair': pair,
        'price': str(price),           
    }
    response = kraken_request('/0/private/AddOrder', data, api_key, api_secret)
    return response


def main():
    data = need_to_place_order()
    if data['Place Trade']:
        if data['Type'] == 'USDC':
            res = place_stop_loss_order("USDCCAD", data['Volume'])
            if 'error' in res and not res['error']:
                print(f'Stop Loss order placed to sell CAD for USDC')
                print(res)
            else:
                print('Error placing stop loss order:', res['error'])
        elif data['Type'] == 'ZCAD':
            res = place_take_profit_order("USDCCAD", data["Volume"])
            if 'error' in res and not res['error']:
                print(f'Take Profit order placed to buy USDC with CAD')
                print(res)
            else:
                print('Error placing take profit order:', res['error'])
    else:
        print("USDC or CAD balances are either zero or held in open orders.")

main()