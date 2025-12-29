seq 2000 2025 | while read y
do
  seq -f "%02g" 1 12 | while read m
  do
    [ -e DAT_ASCII_EURUSD_T_$y$m.csv ] && continue
    timeframe=T
    [ $timeframe == T ] && quote=tick-data-quotes
    [ $timeframe == M1 ] && quote=1-minute-bar-quotes
    url="https://www.histdata.com/download-free-forex-historical-data/?/ascii/$quotes/eurusd/$y/$m"
    tk=$(curl $url | grep -m1 tk | sed 's/.*value="//;s/....$//')
    curl -X POST -d "tk=$tk&date=$y&datemonth=$y$m&platform=ASCII&timeframe=$timeframe&fxpair=EURUSD" \
      -H "Referer: $url" \
      -o me.zip https://www.histdata.com/get.php
    unzip -o me.zip
    sleep 2
  done
done
ls *csv | sed 's/.*T_\(.*\)/mv & data\/\1/' |sh
# T: DateTime Stamp,Bid Quote,Ask Quote
# M1: DateTime Stamp;Bar OPEN Bid Quote;Bar HIGH Bid Quote;Bar LOW Bid Quote;Bar CLOSE Bid Quote
