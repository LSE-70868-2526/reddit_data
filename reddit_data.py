import praw
import pandas as pd
from datetime import datetime

# --- Config ---
TICKERS = ["GME", "TSLA", "KO"]
SUBREDDITS = ["wallstreetbets", "stocks", "investing"]

START_DATE = datetime(2024, 1, 1)
END_DATE   = datetime(2024, 3, 31)

# Prototype mode: limits posts fetched per subreddit per ticker
PROTOTYPE   = True
POST_LIMIT  = 50   # set to None when scaling up

SAVE_TO_DISK = False
OUTPUT_DIR   = "data/reddit"

# --- Reddit API credentials ---
# Get these from https://reddit.com/prefs/apps
reddit = praw.Reddit(
    client_id     = "YOUR_CLIENT_ID",
    client_secret = "YOUR_CLIENT_SECRET",
    user_agent    = "sentiment_prototype by u/YOUR_USERNAME"
)

# --- Helpers ---
def in_date_range(timestamp: float) -> bool:
    dt = datetime.utcfromtimestamp(timestamp)
    return START_DATE <= dt <= END_DATE

def search_posts(subreddit: str, ticker: str, limit: int) -> list[dict]:
    """Search a subreddit for posts mentioning a ticker."""
    results = []
    query = f"{ticker} OR ${ticker}"  # e.g. "GME OR $GME"

    try:
        posts = reddit.subreddit(subreddit).search(
            query, sort="new", time_filter="year", limit=limit
        )
        for post in posts:
            if not in_date_range(post.created_utc):
                continue
            results.append({
                "ticker":     ticker,
                "subreddit":  subreddit,
                "date":       datetime.utcfromtimestamp(post.created_utc).date(),
                "type":       "post",
                "text":       f"{post.title} {post.selftext}".strip(),
                "score":      post.score,        # upvotes
                "num_comments": post.num_comments,
            })
    except Exception as e:
        print(f"  ERROR fetching r/{subreddit} for {ticker}: {e}")

    return results

def fetch_all(tickers, subreddits, limit) -> pd.DataFrame:
    all_rows = []
    for ticker in tickers:
        for sub in subreddits:
            print(f"Fetching r/{sub} for {ticker}...")
            rows = search_posts(sub, ticker, limit)
            print(f"  {len(rows)} posts found")
            all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    if df.empty:
        print("\nWARNING: No data fetched. Check your API credentials and date range.")
        return df

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"\nTotal posts fetched: {len(df)}")
    return df

def summarise(df: pd.DataFrame):
    if df.empty:
        return
    summary = (
        df.groupby(["ticker", "subreddit"])
        .agg(
            posts       = ("text", "count"),
            avg_score   = ("score", "mean"),
            total_comments = ("num_comments", "sum"),
        )
        .round(2)
    )
    print("\n--- Summary ---")
    print(summary.to_string())

# --- Main ---
if __name__ == "__main__":
    limit = POST_LIMIT if PROTOTYPE else None
    df = fetch_all(TICKERS, SUBREDDITS, limit)
    summarise(df)

    if SAVE_TO_DISK and not df.empty:
        import os
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df.to_csv(f"{OUTPUT_DIR}/reddit_posts.csv", index=False)
        print(f"\nSaved to '{OUTPUT_DIR}/reddit_posts.csv'")
    elif not SAVE_TO_DISK:
        print("\nPrototype mode: skipping disk save. Set SAVE_TO_DISK = True to persist.")