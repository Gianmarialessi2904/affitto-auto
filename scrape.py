#!/usr/bin/env python3
"""
Cerca affitti a Modena vicino a viale Toscanini e salva il risultato del giorno in
history/AAAA-MM-GG.json, aggiornando history/index.json (l'elenco dei giorni).
La pagina (index.html) legge l'indice, mostra l'ultimo giorno e permette di
rivedere quelli precedenti. I tuoi link manuali stanno in miei-link.json (li gestisce
la pagina, non questo script).

Lo lancia GitHub Actions ogni mattina. Per provarlo a mano:  python scrape.py
"""
import json, os, re, glob, datetime
from math import radians, sin, cos, asin, sqrt
import requests
from bs4 import BeautifulSoup

# ------------------------- CONFIG (ritocca qui) -------------------------
TARGET = (44.6355, 10.9440)          # viale Toscanini, Modena
MAX_KM = 3.0
MIN_LOCALI, MAX_LOCALI = 2, 3        # 2/3 persone: no monolocali, no singole
TOP_N = 10
ENABLED = ["unimore", "subito"]      # affidabili. Aggiungi "immobiliare","idealista" dopo aver verificato.
HERE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(HERE, "history")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.6",
}

ZONES = {
    "buon pastore":(44.6352,10.9438),"toscanini":(44.6355,10.9440),
    "gottardi":(44.6309,10.9466),"gelmini":(44.6306,10.9472),"araldi":(44.6320,10.9460),
    "morane":(44.6298,10.9381),"policlinico":(44.6386,10.9523),"moreali":(44.6380,10.9510),
    "universit":(44.6300,10.9480),"sant'agnese":(44.6420,10.9460),"san lazzaro":(44.6470,10.9590),
    "amendola":(44.6360,10.9620),"rosselli":(44.6360,10.9620),"musicisti":(44.6440,10.9300),
    "mascagni":(44.6470,10.9300),"viali":(44.6470,10.9270),"centro":(44.6471,10.9252),
    "san faustino":(44.6360,10.9150),"modena":(44.6471,10.9252),
}

# ------------------------- HELPERS -------------------------
def haversine(a,b):
    (la1,lo1),(la2,lo2)=map(lambda p:(radians(p[0]),radians(p[1])),(a,b))
    d=sin((la2-la1)/2)**2+cos(la1)*cos(la2)*sin((lo2-lo1)/2)**2
    return 6371*2*asin(sqrt(d))

def distance(*parts):
    blob=" ".join(p for p in parts if p).lower()
    for k,c in ZONES.items():
        if k in blob: return round(haversine(TARGET,c),2),k
    return None,None

def parse_price(t):
    if not t: return None
    t=t.lower(); amt=r"(\d{1,3}(?:[.\s]\d{3})+|\d{3,5})(?:,\d{1,2})?"
    for pat in (rf"(?:€|euro)\s*{amt}", rf"{amt}\s*(?:€|euro|/?\s*mese|mensil)"):
        m=re.search(pat,t)
        if m:
            n=int(re.sub(r"[^\d]","",m.group(1).split(",")[0]) or 0)
            if 150<=n<=9000: return n
    return None

def parse_mq(t):
    m=re.search(r"(\d{2,3})\s*(?:mq|m²|m2|metri)",(t or "").lower())
    return int(m.group(1)) if m else None

def classify(t):
    t=(t or "").lower()
    if "monolocale" in t: return "Monolocale",1
    if "trilocale" in t or "tre camere" in t or "3 camere" in t: return "Trilocale",3
    if "bilocale" in t or "due camere" in t or "2 camere" in t: return "Bilocale",2
    if re.search(r"\bstanz|singol",t): return "Stanza",1
    if "quadrilocale" in t or "4 camere" in t: return "Quadrilocale",4
    return "Appartamento",None

def get(url): return requests.get(url,headers=HEADERS,timeout=25).text

# ------------------------- SCRAPERS (selettori da VERIFICARE una volta) -------------------------
def scrape_unimore():
    soup=BeautifulSoup(get("https://www.bacheca-alloggi.unimore.it/"),"lxml"); out=[]
    for c in soup.select("div.annuncio, div.card, article, li.annuncio"):  # VERIFICA
        text=c.get_text(" ",strip=True); a=c.find("a",href=True)
        if not a: continue
        tip,loc=classify(text)
        out.append(dict(fonte="Unimore",t=a.get_text(strip=True) or text[:80],
            url=requests.compat.urljoin("https://www.bacheca-alloggi.unimore.it/",a["href"]),
            tip=tip,locali=loc,mq=parse_mq(text),prezzo=parse_price(text),addr=text[:140]))
    return out

def scrape_subito():
    soup=BeautifulSoup(get("https://www.subito.it/annunci-emilia-romagna/affitto/appartamenti/modena/?q=appartamento"),"lxml")
    out,seen=[],set()
    for a in soup.select('a[href*="/annuncio/"], a[href*=".htm"]'):  # VERIFICA
        href=a.get("href","")
        if not href.startswith("http") or href in seen: continue
        seen.add(href); card=a.find_parent(["div","article","li"]) or a
        text=card.get_text(" ",strip=True); tip,loc=classify(text)
        out.append(dict(fonte="Subito",t=a.get_text(strip=True) or text[:80],url=href,
            tip=tip,locali=loc,mq=parse_mq(text),prezzo=parse_price(text),addr=text[:140]))
    return out

SCRAPERS={"unimore":scrape_unimore,"subito":scrape_subito}

# ------------------------- PIPELINE -------------------------
def run():
    raw=[]
    for name in ENABLED:
        try: f=SCRAPERS[name](); print(f"[{name}] {len(f)} grezzi"); raw+=f
        except Exception as e: print(f"[{name}] errore: {e}")
    seen,clean=set(),[]
    for l in raw:
        key=l["url"] or l["t"]
        if key in seen: continue
        seen.add(key)
        if l["locali"] and not (MIN_LOCALI<=l["locali"]<=MAX_LOCALI): continue
        if l["tip"] in ("Monolocale","Stanza"): continue
        d,zk=distance(l.get("addr"),l["t"])
        if d is None or d>MAX_KM: continue
        l["dist"]=d; l["zona"]=(zk or "").title(); l.pop("addr",None)
        clean.append(l)
    clean.sort(key=lambda x:(x["dist"], x["prezzo"] or 9_999_999))
    return clean[:TOP_N]

def _load(path):
    try: return json.load(open(path,encoding="utf-8"))
    except Exception: return None

def _latest_history():
    files=sorted(glob.glob(os.path.join(HIST,"20*.json")))
    return _load(files[-1]) if files else None

def main():
    os.makedirs(HIST,exist_ok=True)
    today=datetime.date.today().isoformat()
    now=datetime.datetime.now().isoformat(timespec="seconds")
    path=os.path.join(HIST,f"{today}.json")
    results=run()
    try:
        rimossi=set(json.load(open(os.path.join(HERE,"rimossi.json"),encoding="utf-8")))
        results=[l for l in results if l.get("url") not in rimossi]
    except Exception:
        pass
    if results:
        day=dict(date=today,generated_at=now,last_fresh=today,fresh=True,
                 count=len(results),target="Viale Toscanini, Modena",listings=results)
    else:
        # niente risultati (selettori da sistemare o portale giù): tengo gli ultimi buoni
        fallback=_load(path) or _latest_history() or {}
        day=dict(date=today,generated_at=now,
                 last_fresh=fallback.get("last_fresh", fallback.get("date","")),
                 fresh=False,count=len(fallback.get("listings",[])),
                 target="Viale Toscanini, Modena",listings=fallback.get("listings",[]))
    json.dump(day,open(path,"w",encoding="utf-8"),ensure_ascii=False,indent=2)

    # aggiorna l'indice dei giorni
    days=sorted(os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(HIST,"20*.json")))
    json.dump(dict(days=days,latest=days[-1] if days else None),
              open(os.path.join(HIST,"index.json"),"w",encoding="utf-8"),
              ensure_ascii=False,indent=2)
    print(f"history/{today}.json -> {day['count']} annunci, fresh={day['fresh']} | {len(days)} giorni in archivio")

if __name__=="__main__": main()
