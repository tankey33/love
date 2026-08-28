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


def douban_trending():
    """Build a truthful Douban-current list with local poster files and direct links."""
    url="https://m.douban.com/rexxar/api/v2/subject_collection/movie_showing/items?start=0&count=20"
    headers={**UA,"Referer":"https://m.douban.com/subject_collection/movie_showing/"}
    try:
        req=urllib.request.Request(url,headers=headers)
        with urllib.request.urlopen(req,timeout=22) as r:
            payload=json.load(r)
        items=payload.get("subject_collection_items") or []
        poster_dir=ROOT/"assets"/"posters"/"trending"
        poster_dir.mkdir(parents=True,exist_ok=True)
        normalized=[]
        stamp=time.strftime("%Y-%m-%d %H:%M UTC",time.gmtime())
        for x in items:
            sid=str(x.get("id") or "")
            title=x.get("title") or x.get("name")
            cover=(x.get("cover") or {}).get("url") or x.get("cover_url")
            local=""
            if sid and cover:
                target=poster_dir/(sid+".jpg")
                try:
                    image_req=urllib.request.Request(cover,headers={**UA,"Referer":"https://movie.douban.com/"})
                    with urllib.request.urlopen(image_req,timeout=18) as src,target.open("wb") as dst:
                        dst.write(src.read())
                    local="assets/posters/trending/"+sid+".jpg"
                except Exception as exc:
                    print("douban poster fallback:",sid,type(exc).__name__)
            rating=x.get("rating") or {}
            normalized.append({
                "title":title,"doubanId":sid,
                "doubanUrl":"https://movie.douban.com/subject/"+sid+"/",
                "posterUrl":local or cover or "",
                "rating":rating.get("value") if isinstance(rating,dict) else rating,
                "year":str(x.get("year") or ""),
                "director":" / ".join(x.get("directors") or []),
                "summary":"豆瓣当前热门","tags":["豆瓣热门"],
                "syncedAt":stamp
            })
        if normalized:
            write("movie-trending.json",normalized)
            print("douban trending:",len(normalized),stamp)
    except Exception as exc:
        print("douban trending fallback:",type(exc).__name__,str(exc))

if __name__=="__main__":
    DATA.mkdir(exist_ok=True)
    douban_trending();chart("music")
    enrich("movies.json","movie",100)
    enrich("music.json","music",160)
