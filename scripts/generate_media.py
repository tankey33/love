#!/usr/bin/env python3
"""Refresh public media charts and artwork for the static gallery."""
from __future__ import annotations
import json, pathlib, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
UA={"User-Agent":"Mozilla/5.0 ChronoLoveGallery/1.0","Accept":"application/json"}

def get_json(url, timeout=18):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def read(name):
    with (DATA/name).open(encoding="utf-8") as f:return json.load(f)

def write(name,data):
    with (DATA/name).open("w",encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)
        f.write("\n")

def artwork(url):
    if not url:return ""
    for old in ("100x100bb","100x100","200x200bb"):
        url=url.replace(old,"600x600bb")
    return url

def wikipedia_image(term):
    params=urllib.parse.urlencode({
        "action":"query","generator":"search","gsrsearch":term+" film",
        "gsrlimit":3,"prop":"pageimages","piprop":"thumbnail",
        "pithumbsize":700,"format":"json","formatversion":2
    })
    try:
        pages=get_json("https://en.wikipedia.org/w/api.php?"+params).get("query",{}).get("pages",[])
        hit=next((p for p in pages if p.get("thumbnail",{}).get("source")),None)
        return hit.get("thumbnail",{}).get("source") if hit else ""
    except Exception as exc:
        print("wikipedia retry:",term,type(exc).__name__)
        return ""

def search(item,kind):
    title=item.get("title","")
    artist=item.get("artist","")
    if kind=="movie":
        # Wikipedia supplies stable, keyless lead images; iTunes remains fallback.
        terms=[item.get("english",""),title]
        for term in [x for x in terms if x]:
            image=wikipedia_image(term)
            if image:
                item["posterUrl"]=image
                item["storeUrl"]="https://en.wikipedia.org/wiki/"+urllib.parse.quote(term.replace(" ","_"))
                return item
        countries=["US","CN"]
    else:
        terms=[" ".join(x for x in (title,artist) if x),title]
        countries=["CN","US"]
    for term in [x for x in terms if x]:
        for country in countries:
            params=urllib.parse.urlencode({
                "term":term,"country":country,"media":kind,
                "entity":"movie" if kind=="movie" else "song","limit":5
            })
            try:
                data=get_json("https://itunes.apple.com/search?"+params)
                hits=data.get("results") or []
                if hits:
                    year=str(item.get("year",""))
                    hit=next((x for x in hits if not year or str(x.get("releaseDate","")).startswith(year)),hits[0])
                    image=artwork(hit.get("artworkUrl100"))
                    if image:
                        item["posterUrl"]=image
                        item["storeUrl"]=hit.get("trackViewUrl") or hit.get("collectionViewUrl")
                        return item
            except Exception as exc:
                print("artwork retry:",title,country,type(exc).__name__)
    print("artwork miss:",title)
    return item

def enrich(name,kind,limit):
    items=read(name)
    targets=[x for x in items[:limit] if not x.get("posterUrl")]
    with ThreadPoolExecutor(max_workers=3 if kind=="movie" else 6) as pool:
        jobs={pool.submit(search,x,kind):x for x in targets}
        for job in as_completed(jobs):job.result()
    write(name,items)

def chart(kind):
    if kind=="music":
        url="https://rss.applemarketingtools.com/api/v2/cn/music/most-played/20/songs.json"
        target="music-trending.json"
    else:
        url="https://rss.applemarketingtools.com/api/v2/cn/movies/top-movies/20/movies.json"
        target="movie-trending.json"
    try:
        results=get_json(url).get("feed",{}).get("results",[])
        normalized=[]
        for x in results:
            normalized.append({
                "title":x.get("name"),"artist":x.get("artistName") if kind=="music" else None,
                "director":x.get("artistName") if kind=="movie" else None,
                "year":(x.get("releaseDate") or "")[:4],"genre":x.get("genres",[{}])[0].get("name"),
                "tags":["实时榜单"],"summary":"Apple "+("Music" if kind=="music" else "Movies")+" 中国区榜单",
                "posterUrl":artwork(x.get("artworkUrl100")),"storeUrl":x.get("url")
            })
        if normalized:write(target,normalized)
    except Exception as exc:
        print("chart fallback:",kind,type(exc).__name__)

if __name__=="__main__":
    DATA.mkdir(exist_ok=True)
    chart("movie");chart("music")
    enrich("movies.json","movie",100)
    enrich("music.json","music",160)
