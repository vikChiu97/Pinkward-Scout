import os, urllib.parse, requests
from dotenv import load_dotenv
import json

load_dotenv()
KEY = os.getenv("RIOT_API_KEY")
HDR = {"X-Riot-Token": KEY}

REGIONAL = {"NA1":"americas","BR1":"americas","LA1":"americas","LA2":"americas","OC1":"americas",
            "EUW1":"europe","EUN1":"europe","TR1":"europe","RU":"europe",
            "KR":"asia","JP1":"asia"}
PLATFORM = {"NA1":"na1","BR1":"br1","LA1":"la1","LA2":"la2","OC1":"oc1",
            "EUW1":"euw1","EUN1":"eun1","TR1":"tr1","RU":"ru","KR":"kr","JP1":"jp1"}

def key_ok(platform="na1"):
    r = requests.get(f"https://{platform}.api.riotgames.com/lol/platform/v3/champion-rotations", headers=HDR)
    return r.ok

def puuid_from_riot_id(gameName, tagLine):
    g, t = urllib.parse.quote(gameName), urllib.parse.quote(tagLine)
    region = REGIONAL.get(tagLine.upper())
    if not region:
        return None
    r = requests.get(f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{g}/{t}", headers=HDR)
    
    return r.json().get("puuid") if r.ok else None, PLATFORM.get(tagLine.upper())

def summoner_by_puuid(puuid, platform):
    r = requests.get(f"https://{platform}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}", headers=HDR)
    return r.json() if r.ok else None

if __name__ == "__main__":
    if not key_ok("na1"):
        raise SystemExit("API key not accepted on platform route.")
    riot_id = input("Enter Riot ID (Name#Tag): ").strip()
    if "#" not in riot_id: raise SystemExit("Use format Name#Tag (e.g., Pinkward#NA1).")
    name, tag = riot_id.split("#", 1)
    puuid, platform = puuid_from_riot_id(name, tag)
    if not puuid or not platform: raise SystemExit("Riot ID not found or unsupported tag.")
    summ = summoner_by_puuid(puuid, platform)
    if not summ: raise SystemExit("Failed to fetch Summoner by PUUID.")
    print(json.dumps(summ, indent=2, sort_keys=True))
    # print({k: summ[k] for k in ("name","puuid","summonerLevel") if k in summ})
