#!/Users/jerry/trade/myvenv/bin/python
import csv
import sys
import glob
import time
import random
import os.path
import pandas as pd
import numpy as np
from colorama import init as colorama_init
from colorama import Fore
from colorama import Style

colorama_init()


# ===================== CONFIG =====================

PIP = 0.0001
TAKE_PROFIT = 20
STOP_LOSS = 2000
TRADE_INTERVAL = 86400 * 3

EMA_FAST = 50
EMA_SLOW = 200

# ===================== LOAD DATA =====================

def ticks():
  data_path = "./data/2025*.csv"   # path to YYYYMM.csv files
  for fname in sorted(glob.glob(data_path)):
    if os.path.basename(fname) < '2015':
      continue
    print(f"Reading file {fname}")
    df = pd.read_csv(
      fname,
      header=None,
      usecols=[0, 1, 2, 3],
      names=["date", "time", "bid", "ask"],
      dtype={"date": "str", "time": "str", "bid": "float32", "ask": "float32"},
    )
    # vectorised datetime parsing
    dt = pd.to_datetime(
      df["date"] + " " + df["time"],
      format="%Y%m%d %H%M%S%f",
    )
    # convert once
    for dt, bid, ask in zip(dt.values, df["bid"].values, df["ask"].values):
      yield dt, bid, ask

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
  iter_ticks = ticks()
  next_trade_time = next(iter_ticks)[0] + np.timedelta64(wait_seconds, "s")
  trend_detector = TrendDetector()

  for dt, bid, ask in iter_ticks:
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
      next_trade_time = close_time + np.timedelta64(wait_seconds, "s")

  return orders, total_pips

def print_order(entry, idx=0):
  color = Fore.GREEN if entry['direction'] == 'BUY' else Fore.YELLOW
  print(
    f"{idx:03d} | {color}{entry['direction']:4s}{Style.RESET_ALL} | "
    #f"{idx:03d} | {entry['direction']:4s} | "
    f"Open: {entry['open_time'].astype(str)[:-6]} @ {entry['open_price']:.5f} | "
    f"Close: {entry['close_time'].astype(str)[:-6]} @ {entry['close_price']:.5f} | "
    f"Pips: {entry['pips']:.1f}"
  )


# ===================== REPORT =====================

def main():
  orders, total_pips = test()
  print(f"Total orders: {len(orders)}")
  print(f"Total pips: {total_pips:.2f}")
  open('record.txt', 'a').write(f"{total_pips:.2f}\n")

main()
