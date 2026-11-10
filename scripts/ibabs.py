"""Haalt de openbare vergaderkalender van almelo.bestuurlijkeinformatie.nl (iBabs) op voor de agenda in de app.

Gebruik: python3 scripts/ibabs.py uit.json
Neemt raad, hamerraad en politieke avonden mee van 14 dagen terug tot 6 maanden vooruit,
met per vergadering de agendapunten (Politieke avond 1/2 met onderwerpen). B&W-vergaderingen niet.
Alleen openbare vergaderingen: wat alleen na inloggen in iBabs staat (presidium, symposia,
raadsledendagen) zit hier niet in en moet via de inzendmap.
"""
import datetime as dt, html, json, re, sys, urllib.request

BASIS = "https://almelo.bestuurlijkeinformatie.nl"
UA = {"User-Agent": "pvv-almelo-app/1.0", "X-Requested-With": "XMLHttpRequest"}


def get(pad):
    req = urllib.request.Request(BASIS + pad, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def tekst(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def onderwerpen(pad):
    """Korte omschrijving: de agendapunten van de vergadering of sessie (zonder vaste punten)."""
    try:
        h = get(pad)
    except Exception:
        return ""
    vast = re.compile(r"^(Opening|Sluiting|Vaststellen (van de )?agenda|Mededelingen|Rondvraag|Besluitenlijst|Ingekomen stukken|Vragenhalfuur)", re.I)
    if "/Agenda/Session/" in pad:
        delen = []
        for blok in re.split(r'<div class="row first-header">', h)[1:]:
            naam = tekst(re.search(r"<a [^>]*>(.*?)</a>", blok, re.S).group(1)) if "<a " in blok else ""
            punten = [tekst(x) for x in re.findall(r'class="timeline-details">\s*<a [^>]*>(.*?)</a>', blok, re.S)]
            punten = [re.sub(r"^\d+\.\s*|\s*-\s*(Raadzaken|Tijd:.*)$", "", x).strip() for x in punten]
            punten = [re.sub(r"\s*-\s*Tijd:.*$", "", x) for x in punten]
            if punten:
                delen.append(f"{naam}: " + "; ".join(punten))
        t = " · ".join(delen)
    else:
        punten = [tekst(x) for x in re.findall(r'class="panel-title-label"\s*>(.*?)</span>', h, re.S)]
        t = "; ".join(x for x in punten if not vast.match(x))
    if not t:
        return "Agenda nog niet gepubliceerd."
    return t[:400] + ("…" if len(t) > 400 else "")


def main(uit):
    nu = dt.date.today()
    start, eind = nu - dt.timedelta(days=14), nu + dt.timedelta(days=183)
    lijst = json.loads(get(f"/Calendar/GetAgendasForCalendar?start={start}&end={eind}"))
    events = []
    for e in lijst:
        titel = e.get("title", "")
        if "10000036" in " ".join(e.get("classNames", [])) or titel.startswith("B&W"):
            continue
        soort = "raad" if re.match(r"(Hamer)?[Rr]aad", titel) else "beraad"
        ev = {"t": e["start"][:16], "type": soort, "title": titel,
              "desc": onderwerpen(e["url"]), "link": BASIS + e["url"], "bron": "ibabs"}
        eind_t = (e.get("end") or "")[:16]
        ev["end"] = eind_t if eind_t[:10] == e["start"][:10] and eind_t[11:] not in ("", "00:00") else e["start"][:10] + "T23:00"
        events.append(ev)
    json.dump({"opgehaald": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "events": events},
              open(uit, "w"), ensure_ascii=False, indent=1)
    print(len(events), "vergaderingen")


if __name__ == "__main__":
    main(sys.argv[1])
