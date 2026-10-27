"""Haalt nieuwskoppen op voor de tab Nieuws (Oost, 1Twente, NOS, Tweede en Eerste Kamer) en schrijft nieuws.json.

Alleen kop, datum, bron en link; geen intro's of foto's (auteursrecht).
Valt een bron uit, dan blijven de koppen van de vorige run staan.
Gebruik: python3 nieuws.py vorige.json nieuws.json
"""
import json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET

UA = {"User-Agent": "pvv-almelo-app nieuwsoverzicht (github.com/Rijkenk/pvv-almelo-app)"}
NU = datetime.now(timezone.utc)
# Onderwerpen waarbij een Kamerdebat meestal doorwerkt in de gemeente
GEMEENTE = re.compile(r"gemeente|gemeentefonds|decentrali|jeugd|wmo|participatie|bijstand|asiel|opvang|spreiding|"
                      r"statushouder|arbeidsmigr|woning|huisvesting|volkshuisvesting|politie|veiligheid|ondermijning|"
                      r"energie|warmte|stikstof|onderwijs|armoede|schuld|zorg|ozb|belasting", re.I)

def get(url, accept=None):
    h = dict(UA)
    if accept: h["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
        return r.read()

def iso(s):
    try: return parsedate_to_datetime(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception: return ""

def rss(url, bron):
    root = ET.fromstring(get(url))
    items = []
    for it in root.iter("item"):
        titel, link = (it.findtext("title") or "").strip(), (it.findtext("link") or "").strip()
        if titel and link.startswith("https://"):
            items.append({"titel": titel, "link": link, "datum": iso(it.findtext("pubDate") or ""), "bron": bron})
    if not items: raise ValueError("lege feed")
    return items

def almelo(i): return "almelo" in i["titel"].lower()

def woorden(titel):
    return {w for w in re.findall(r"\w+", titel.lower()) if len(w) > 3}

def dubbel(a, b):
    # Zelfde nieuws bij twee omroepen: (bijna) dezelfde kop
    wa, wb = woorden(a["titel"]), woorden(b["titel"])
    return bool(wa and wb) and len(wa & wb) / min(len(wa), len(wb)) >= 0.6

def oost():
    twente = rss("https://www.oost.nl/rss/twente.xml", "Oost")
    alles = rss("https://www.oost.nl/rss/nieuws.xml", "Oost")
    return twente + [i for i in alles if almelo(i)]

def een_twente():
    eigen = rss("https://www.1twente.nl/feed/almelo", "1Twente")
    for i in eigen: i["almelo"] = True
    return eigen + rss("https://www.1twente.nl/feed/politiek", "1Twente")

def lokaal(vorig):
    # Elke omroep apart ophalen; valt er één uit, dan blijven diens vorige koppen staan.
    items, fouten = [], []
    for bron, fn in (("Oost", oost), ("1Twente", een_twente)):
        try: items += fn()
        except Exception as e:
            fouten.append(f"{bron}: {e}")
            items += [i for i in vorig.get("lokaal", []) if i.get("bron") == bron]
    if not items: raise ValueError("; ".join(fouten))
    uit = []
    for i in sorted(items, key=lambda i: i["bron"] != "Oost"):  # Oost eerst; 1Twente vult aan zonder dubbele koppen
        if any(i["link"] == j["link"] or dubbel(i, j) for j in uit): continue
        i["almelo"] = i.get("almelo") or almelo(i); uit.append(i)
    uit.sort(key=lambda i: i["datum"], reverse=True)
    if fouten: print("; ".join(fouten), file=sys.stderr)
    return uit[:40]

def nos():
    return rss("https://feeds.nos.nl/nosnieuwspolitiek", "NOS")[:20]

def tweede_kamer():
    van, tot = NU.strftime("%Y-%m-%d"), (NU + timedelta(days=14)).strftime("%Y-%m-%d")
    filt = (f"Verwijderd eq false and Datum ge {van}T00:00:00Z and Datum le {tot}T23:59:59Z and "
            "(startswith(Soort,'Plenair debat') or Soort eq 'Commissiedebat' or Soort eq 'Wetgevingsoverleg' or Soort eq 'Notaoverleg')")
    q = urllib.parse.urlencode({"$filter": filt, "$orderby": "Datum", "$top": "250",
                                "$select": "Soort,Nummer,Onderwerp,Datum,Status"}, quote_via=urllib.parse.quote)
    fout = None
    for basis in ("https://gegevensmagazijn.tweedekamer.nl/OData/v5", "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"):
        try: rijen = json.loads(get(f"{basis}/Activiteit?{q}", "application/json"))["value"]; break
        except Exception as e: fout = e
    else: raise fout
    uit = []
    for a in rijen:
        if a.get("Status") in ("Geannuleerd", "Vervallen") or not a.get("Onderwerp"): continue
        plenair = a["Soort"].startswith("Plenair")
        relevant = bool(GEMEENTE.search(a["Onderwerp"]))
        if not (plenair or relevant): continue  # commissiedebatten alleen als ze gemeenten raken
        pad = ("plenaire_vergaderingen/details/activiteit" if plenair else "commissievergaderingen/details")
        uit.append({"titel": a["Onderwerp"].strip(), "soort": a["Soort"], "datum": a["Datum"], "bron": "Tweede Kamer",
                    "link": f"https://www.tweedekamer.nl/debat_en_vergadering/{pad}?id={a['Nummer']}", "gemeente": relevant})
    return uit[:40]

def eerste_kamer():
    # De Eerste Kamer biedt (voor zover bekend) geen vaste nieuwsfeed; probeer de bekende adressen.
    for url in ("https://www.eerstekamer.nl/rss/nieuws", "https://www.eerstekamer.nl/rss_nieuws", "https://www.eerstekamer.nl/rss"):
        try: return rss(url, "Eerste Kamer")[:15]
        except Exception: pass
    raise ValueError("geen feed gevonden")

BRONNEN = {"lokaal": lokaal, "kamer": tweede_kamer, "landelijk": nos, "eerstekamer": eerste_kamer}

def main(vorig_pad, uit_pad):
    try: vorig = json.load(open(vorig_pad, encoding="utf-8"))
    except Exception: vorig = {}
    uit = {"bijgewerkt": NU.strftime("%Y-%m-%dT%H:%M:%SZ"), "status": {}}
    for naam, fn in BRONNEN.items():
        try:
            uit[naam] = fn(vorig) if naam == "lokaal" else fn(); uit["status"][naam] = {"ok": True, "sinds": uit["bijgewerkt"]}
        except Exception as e:
            uit[naam] = vorig.get(naam, [])
            oud = vorig.get("status", {}).get(naam, {})
            uit["status"][naam] = {"ok": False, "fout": str(e)[:200], "sinds": oud.get("sinds", "")}
            print(f"{naam}: {e}", file=sys.stderr)
    with open(uit_pad, "w", encoding="utf-8") as f:
        json.dump(uit, f, ensure_ascii=False, indent=1)
    print({k: len(uit[k]) for k in BRONNEN})

if __name__ == "__main__":
    main(*sys.argv[1:3])
