import os, requests, json, random, time, pathlib
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("RIOT_API_KEY")
HDR = {"X-Riot-Token": KEY}
PLATFORM = "na1"
REGIONAL = "americas"

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
    return list(dict.fromkeys(pool))

def sample_puuids(count=1, tier="GOLD"):
    pool = pool_puuids(tier=tier, divisions=("I","II","III","IV"), pages_per_div=1)
    if not pool:
        return []
    return random.sample(pool, min(count, len(pool)))

def get_recent_match_ids(puuid, count=20, queue=None, start=0):
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

def get_match(match_id):
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    r = requests.get(url, headers=HDR)
    if not r.ok:
        try: body = r.json()
        except: body = r.text[:400]
        raise RuntimeError(f"match {match_id} -> {r.status_code}: {body}")
    return r.json()

def get_timeline(match_id):
    url = f"https://{REGIONAL}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    r = requests.get(url, headers=HDR)
    if not r.ok:
        try: body = r.json()
        except: body = r.text[:400]
        raise RuntimeError(f"timeline {match_id} -> {r.status_code}: {body}")
    return r.json()

def dump_json(obj, path):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return str(path.resolve())

# ========= Jungle filter utilities =========
JUNGLE_MONSTER_TYPES = {
    # Elite objectives
    "DRAGON", "RIFTHERALD", "BARON_NASHOR", "ATAKHAN", "VOIDGRUB",
    # Regular camps (names vary by patch)
    "BLUE_SENTINEL", "RED_BRAMBLEBACK", "GROMP", "KRUGS", "RAPTORS",
    "MURKWOLVES", "SCUTTLE_CRAB"
}

def iter_events(timeline_json):
    for fr in timeline_json.get("info", {}).get("frames", []):
        for ev in fr.get("events", []):
            yield ev

def is_jungle_event(ev):
    t = ev.get("type")
    if t == "ELITE_MONSTER_KILL":
        return True
    if t == "MONSTER_KILL":
        m = ev.get("monsterType") or ev.get("monsterSubType") or ev.get("monsterTypeName")
        # If the field is missing, keep it so you can inspect and refine the allowlist later
        return True if m is None else (str(m).upper() in JUNGLE_MONSTER_TYPES)
    return False

def ms_to_mmss(ms):
    s = ms // 1000
    return f"{s//60:02d}:{s%60:02d}"

def filter_jungle_events(timeline_json):
    out = []
    for ev in iter_events(timeline_json):
        if is_jungle_event(ev):
            ev2 = dict(ev)
            ts = ev2.get("timestamp")
            if isinstance(ts, int):
                ev2["clock"] = ms_to_mmss(ts)
            out.append(ev2)
    out.sort(key=lambda e: e.get("timestamp", 0))
    return out
# ==========================================

if __name__ == "__main__":
    # 1) Pick one GOLD player
    puuids = sample_puuids(count=1, tier="GOLD")
    if not puuids:
        raise SystemExit("No PUUIDs found.")
    puuid = puuids[0]
    print(f"Picked PUUID: {puuid}")

    # 2) Get last 20 ranked solo match IDs
    match_ids = get_recent_match_ids(puuid, count=20, queue=420)
    if not match_ids:
        raise SystemExit("No recent ranked matches for this player.")
    match_id = match_ids[0]
    print(f"Picked match: {match_id}")

    # 3) Fetch full match and timeline
    match_json = get_match(match_id)
    timeline_json = get_timeline(match_id)

    # 4) Print ALL metadata blocks (unfiltered)
    print("\n=== MATCH METADATA (full) ===")
    print(json.dumps(match_json.get("metadata", {}), indent=2, sort_keys=True))

    print("\n=== TIMELINE METADATA (full) ===")
    print(json.dumps(timeline_json.get("metadata", {}), indent=2, sort_keys=True))

    # 5) Save full raw JSON to disk
    out_dir = "riot_dump"
    match_path = dump_json(match_json, f"{out_dir}/{match_id}.match.json")
    timeline_path = dump_json(timeline_json, f"{out_dir}/{match_id}.timeline.json")
    print(f"\nSaved full payloads:\n- {match_path}\n- {timeline_path}")

    # 6) NEW: filter jungle/neutral events and save a cleaned view
    jungle_events = filter_jungle_events(timeline_json)
    jungle_path = dump_json(jungle_events, f"{out_dir}/{match_id}.jungle_events.json")
    print(f"\nKept {len(jungle_events)} jungle/neutral events → {jungle_path}")

    # Preview first few events for a quick look
    for ev in jungle_events[:8]:
        print(json.dumps(ev, indent=2)[:800], "\n---")
