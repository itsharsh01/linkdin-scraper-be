import json
import os
from pathlib import Path
import sys

from apify_client import ApifyClient


def load_env_file():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file()
api_token = os.getenv("APIFY_CLIENT_KEY")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

if not api_token:
    raise ValueError("APIFY_CLIENT_KEY is missing from the environment.")

# Initialize the ApifyClient with your API token
client = ApifyClient(api_token)

# Prepare the Actor input
scrape_until = None

run_input = {
    "urls": [
        "https://www.linkedin.com/search/results/content/?keywords=hiring%20ai%20engineer&origin=FACETED_SEARCH&sortBy=%5B%22relevance%22%5D&datePosted=%5B%22past-24h%22%5D",
        "https://www.linkedin.com/search/results/content/?keywords=hiring%20remote%20%20ai%20engineer%20usa&origin=GLOBAL_SEARCH_HEADER&sortBy=%5B%22relevance%22%5D&datePosted=%5B%22past-24h%22%5D"
    ],
    "limitPerSource": 1,
    "deepScrape": True,
    "rawData": False,
}

if scrape_until:
    run_input["scrapeUntil"] = scrape_until

# Run the Actor and wait for it to finish
run = client.actor("Wpp1BZ6yGWjySadk3").call(run_input=run_input)

# Fetch Actor results and save them to a JSON file
items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
output_path = Path(__file__).with_name("scraped_items.json")

output_path.write_text(
    json.dumps(items, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(f"Saved {len(items)} items to {output_path}")