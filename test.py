import csv
import sys
import glob
import time
import random
import os.path
from datetime import datetime, timedelta
#from colorama import init as colorama_init
#from colorama import Fore
#from colorama import Style

#colorama_init()


# ===================== CONFIG =====================

PIP = 0.0001
TAKE_PROFIT = 20
STOP_LOSS = 200
TRADE_INTERVAL = 86400 * 2

EMA_FAST = 50
EMA_SLOW = 200

# ===================== LOAD DATA =====================

def ticks():
  data_path = "./data/2025*.csv"   # path to YYYYMM.csv files
  for fname in sorted(glob.glob(data_path)):
    if os.path.basename(fname) < '2015':
      continue
    print(f"Reading file {fname}")
    with open(fname, "r") as f:
      reader = csv.reader(f)
      for row in reader:
        dt = datetime.strptime(
          f"{row[0]} {row[1][:-3]}", "%Y%m%d %H%M%S"
        )
        bid = float(row[2])
        ask = float(row[3])
        yield dt, bid, ask
    time.sleep(10)

# ===================== BACKTEST =====================

class TrendDetector:
  up = 1
  down = -1
  irange = 0
  confirm_ticks = 20

  def __init__(self):
    self.ema_fast = None
    self.ema_slow = None
    self.alpha_fast = 2 / (EMA_FAST + 1)
    self.alpha_slow = 2 / (EMA_SLOW + 1)
    self.last_raw_trend = self.irange
    self.confirmed_trend = self.irange
    self.confirm_count = 0


  def update(self, price):
    if self.ema_fast is None:
      # initialize
      self.ema_fast = price
      self.ema_slow = price
      return self.irange

    self.ema_fast = (
      price * self.alpha_fast
        + self.ema_fast * (1 - self.alpha_fast)
    )
    self.ema_slow = (
      price * self.alpha_slow
        + self.ema_slow * (1 - self.alpha_slow)
    )

    if self.ema_fast > self.ema_slow:
      raw_trend = self.up
    elif self.ema_fast < self.ema_slow:
      raw_trend = self.down
    else:
      raw_trend = self.irange
    # confirmation logic
    if raw_trend == self.last_raw_trend:
        self.confirm_count += 1
    else:
        self.confirm_count = 1
        self.last_raw_trend = raw_trend

    if self.confirm_count >= self.confirm_ticks:
        self.confirmed_trend = raw_trend

    return self.confirmed_trend

def test():
  orders = []
  total_pips = 0.0
  in_trade = False
  wait_seconds = random.randint(0, TRADE_INTERVAL)
  next_trade_time = next(ticks())[0] + timedelta(seconds=wait_seconds)
  trend_detector = TrendDetector()

  for dt, bid, ask in ticks():
    mid = (bid + ask) / 2
    trend = trend_detector.update(mid)

    # wait until allowed to open next trade
    if not in_trade and dt < next_trade_time:
        continue

    # ---------------- OPEN TRADE ----------------
    if not in_trade:
      if trend == trend_detector.irange:
        continue  # skip chop
      # trend-following random
      if trend == trend_detector.up:
        direction = "BUY"
        open_price = ask
      elif trend == trend_detector.down:
        direction = "SELL"
        open_price = bid

      open_time = dt
      in_trade = True
      continue

    # ---------------- CHECK EXIT ----------------
    if direction == "BUY":
      current_pips = (bid - open_price) / PIP
    else:
      current_pips = (open_price - ask) / PIP

    if current_pips >= TAKE_PROFIT or current_pips <= -STOP_LOSS:
      close_time = dt
      if direction == "BUY":
        close_price = bid
      else:
        close_price = ask
      entry = {
        "direction": direction,
        "open_time": open_time,
        "close_time": close_time,
        "open_price": open_price,
        "close_price": close_price,
        "pips": current_pips
      }
      print_order(entry, len(orders))
      orders.append(entry)
      total_pips += current_pips
      in_trade = False

      wait_seconds = random.randint(0, TRADE_INTERVAL)
      next_trade_time = close_time + timedelta(seconds=wait_seconds)

  return orders, total_pips

def print_order(entry, idx=0):
  #color = Fore.GREEN if entry['direction'] == 'BUY' else Fore.Yellow
  print(
    #f"{idx:03d} | {Fore.GREEN}{entry['direction']:4s}{Style.RESET_ALL} | "
    f"{idx:03d} | {entry['direction']:4s} | "
    f"Open: {entry['open_time']} @ {entry['open_price']:.5f} | "
    f"Close: {entry['close_time']} @ {entry['close_price']:.5f} | "
    f"Pips: {entry['pips']:.1f}"
  )


# ===================== REPORT =====================

def main():
  orders, total_pips = test()
  print(f"Total orders: {len(orders)}")
  print(f"Total pips: {total_pips:.2f}")
  open('record.txt', 'a').write(f"{total_pips:.2f}\n")

main()
