import requests
import pandas as pd
import time
import datetime as dt
import yfinance as yf
import os

HEADERS = {"User-Agent": "Mozilla/5.0"}


# -----------------------------
# 1️⃣ Get Nifty 200 List
# -----------------------------
def get_nifty200():
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20200"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    data = resp.json()
    symbols = [item["symbol"] for item in data["data"]]
    return symbols


# -----------------------------
# 2️⃣ Get Shareholding Pattern
# -----------------------------
def get_shareholding(symbol):
    url = f"https://www.nseindia.com/api/corporate-share-holdings?symbol={symbol}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        return None
    return resp.json()


# -----------------------------
# 3️⃣ Extract FII/DII Trend (3 quarters)
# -----------------------------
def extract_trend(js):
    qdata = js.get("data", [])
    if len(qdata) < 3:
        return None

    # First 3 quarters
    q3 = qdata[:3]

    fii = [float(q["foreignInstitutions"]) for q in q3]
    dii = [float(q["domesticInstitutions"]) for q in q3]

    return fii, dii


# -----------------------------
# 4️⃣ Daily market-wide FII/DII flow
# -----------------------------
def daily_flow_sentiment():
    url = "https://www.nseindia.com/api/fiidiiTradeReact?date=&category=all"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    
    try:
        js = resp.json()
    except:
        return 0, 0  # fallback when API returns invalid JSON

    # Case 1: js is a dictionary (normal)
    if isinstance(js, dict) and "data" in js:
        df = pd.DataFrame(js["data"])

    # Case 2: js itself is a list (NSE alternate format)
    elif isinstance(js, list):
        df = pd.DataFrame(js)

    # Case 3: unexpected format
    else:
        return 0, 0

    try:
        df["netFII"] = df["fiiBuyValue"] - df["fiiSellValue"]
        df["netDII"] = df["diiBuyValue"] - df["diiSellValue"]
    except:
        return 0, 0

    last15 = df.head(15)
    return last15["netFII"].sum(), last15["netDII"].sum()
    
# -----------------------------
# 5️⃣ Technical Check
# -----------------------------
def tech_signal(symbol):
    try:
        df = yf.download(symbol + ".NS", period="6mo", progress=False)
        df["SMA200"] = df["Close"].rolling(200).mean()
        last = df.iloc[-1]
        return last["Close"] > last["SMA200"]
    except:
        return False


# -----------------------------
# 6️⃣ Main Runner
# -----------------------------
def main():
    print("Fetching Nifty200…")
    symbols = get_nifty200()

    smart_list = []

    print(f"Total symbols: {len(symbols)}")

    for i, sym in enumerate(symbols):
        print(f"Processing {i+1}/{len(symbols)}: {sym}")

        try:
            js = get_shareholding(sym)
            if not js:
                continue

            trend = extract_trend(js)
            if not trend:
                continue

            fii, dii = trend

            if fii[0] < fii[1] < fii[2] and dii[0] < dii[1] < dii[2]:
                tech = tech_signal(sym)
                smart_list.append([sym, fii, dii, tech])

            time.sleep(0.5)

        except Exception as e:
            print(f"Error processing {sym}: {e}")
            time.sleep(1)

    df = pd.DataFrame(smart_list, columns=["Symbol", "FII(3Q)", "DII(3Q)", "Above200DMA"])

    fii_flow, dii_flow = daily_flow_sentiment()
    df["FII_15d_Flow"] = fii_flow
    df["DII_15d_Flow"] = dii_flow
    df["Verdict"] = df["Above200DMA"].apply(lambda x: "BUY" if x else "WATCH")

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    excel_file = f"smart_money_{timestamp}.xlsx"

    df.to_excel(excel_file, index=False)

    # ----- Summary text -----
    prev_file = "previous_smart_list.txt"
    current_set = set(df["Symbol"])

    added = removed = []

    if os.path.exists(prev_file):
        old = set(open(prev_file).read().splitlines())
        added = sorted(current_set - old)
        removed = sorted(old - current_set)

    with open(prev_file, "w") as f:
        f.write("\n".join(current_set))

    summary = (
        f"📊 Smart Money Tracker ({dt.datetime.now():%d %b %Y})\n"
        f"Total qualified: {len(df)}\n"
        f"New additions: {len(added)} → {', '.join(added)}\n"
        f"Removed: {len(removed)} → {', '.join(removed)}\n"
        f"FII 15d Flow: ₹{int(fii_flow)} Cr\n"
        f"DII 15d Flow: ₹{int(dii_flow)} Cr\n"
    )

    with open("summary.txt", "w") as f:
        f.write(summary)

    print(summary)

    return excel_file, "summary.txt"


if __name__ == "__main__":
    main()
