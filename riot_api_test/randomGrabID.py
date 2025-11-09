import os, requests, json, random, time
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("RIOT_API_KEY")
HDR = {"X-Riot-Token": KEY}
PLATFORM = "na1"         # platform routes (summoner/league)
REGIONAL = "americas"    # regional route for Match-V5 when PLATFORM is NA1

def fetch_entries(tier="GOLD", division="I", page=1):
    url = f"https://{PLATFORM}.api.riotgames.com/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{division}?page={page}"
    r = requests.get(url, headers=HDR)
    if not r.ok:
        try: body = r.json()
        except: body = r.text[:400]
        raise RuntimeError(f"entries {tier} {division} p{page} -> {r.status_code}: {body}")
    data = r.json()
    return data if isinstance(data, list) else []

def pool_puuids(tier="GOLD", divisions=("I","II","III","IV"), pages_per_div=1, sleep=0.03):
    pool = []
    for div in divisions:
        for p in range(1, pages_per_div + 1):
            es = fetch_entries(tier=tier, division=div, page=p)
            if not es:
                break
            pool.extend(e["puuid"] for e in es if e.get("puuid"))
            time.sleep(sleep)
    return list(dict.fromkeys(pool))  # dedupe

def sample_puuids(count=20, tier="GOLD"):
    pool = pool_puuids(tier=tier, divisions=("I","II","III","IV"), pages_per_div=1)
    if not pool:
        return []
    k = min(count, len(pool))
    return random.sample(pool, k)

# === NEW: fetch last N match IDs for a PUUID from the regional host ===
def get_recent_match_ids(puuid, count=20, queue=None, start=0):
    """
    queue: set to 420 for Ranked Solo only, or None for all queues
    """
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"start": start, "count": count}
    if queue is not None:
        params["queue"] = queue
    r = requests.get(url, headers=HDR, params=params)
    if not r.ok:
        try: body = r.json()
        except: body = r.text[:400]
        raise RuntimeError(f"match ids -> {r.status_code}: {body}")
    return r.json()

if __name__ == "__main__":
    # 1) Grab one random GOLD player
    puuids = sample_puuids(count=1, tier="GOLD")
    if not puuids:
        raise SystemExit("No PUUIDs found from league entries.")
    puuid = puuids[0]
    print(f"Picked PUUID: {puuid}")

    # 2) Get last 20 matches (all queues). Use queue=420 to limit to Ranked Solo.
    match_ids = get_recent_match_ids(puuid, count=20, queue=420)
    print(json.dumps({"match_count": len(match_ids), "match_ids": match_ids}, indent=2))
