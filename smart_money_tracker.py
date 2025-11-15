import requests, pandas as pd, time, datetime as dt, yfinance as yf, os

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ---------- (functions from previous version stay the same) ----------
# get_nifty200(), get_shareholding(), extract_trend(), daily_flow_sentiment(), tech_signal()
# ---------------------------------------------------------------------

def main():
    symbols = get_nifty200()
    print(f"Loaded {len(symbols)} Nifty200 symbols")
    smart = []

    for i, sym in enumerate(symbols):
        try:
            js = get_shareholding(sym)
            if not js:
                continue
            fii, dii = extract_trend(js)
            if fii[0] < fii[1] < fii[2] and dii[0] < dii[1] < dii[2]:
                tech = tech_signal(sym)
                smart.append([sym, fii, dii, tech])
            time.sleep(0.5)
        except Exception as e:
            print(f"{sym}: {e}")
            time.sleep(1)

    df = pd.DataFrame(smart, columns=["Symbol","FII(3Q)","DII(3Q)","Above200DMA"])
    fii_flow, dii_flow = daily_flow_sentiment()
    df["FII_15d_flow(₹Cr)"] = fii_flow
    df["DII_15d_flow(₹Cr)"] = dii_flow
    df["Verdict"] = df["Above200DMA"].apply(lambda x: "✅ BUY" if x else "Watch")

    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M")
    out = f"smart_money_{stamp}.xlsx"
    df.to_excel(out, index=False)

    # --- Build daily summary text for email ---
    prev_file = "previous_smart_list.txt"
    current_set = set(df["Symbol"])
    added, removed = [], []
    if os.path.exists(prev_file):
        with open(prev_file) as f:
            old = set(f.read().splitlines())
        added = sorted(current_set - old)
        removed = sorted(old - current_set)
    with open(prev_file, "w") as f:
        f.write("\n".join(current_set))

    summary = (
        f"📊 Smart Money Tracker Report – {dt.datetime.now():%d %b %Y}\n"
        f"------------------------------------------\n"
        f"Total qualified stocks: {len(df)}\n"
        f"New additions: {len(added)}\n"
        f"Removed: {len(removed)}\n"
        f"FII 15-day flow = ₹{int(fii_flow):,} Cr\n"
        f"DII 15-day flow = ₹{int(dii_flow):,} Cr\n\n"
        f"New stocks → {', '.join(added) if added else 'None'}\n"
        f"Removed → {', '.join(removed) if removed else 'None'}\n"
    )
    with open("summary.txt","w") as f:
        f.write(summary)
    print(summary)
    return out, "summary.txt"

if __name__ == "__main__":
    main()
