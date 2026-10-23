# Fractie-app PVV Almelo

Web-app voor de fractie (agenda, actiepunten, raadsupdate, standpunten, spelregels, wie is wie). Draait op GitHub Pages en kan op iPhone en Android op het beginscherm worden gezet.

## Bestanden
- `index.html`: de app.
- `data.json`: agenda (`events`), actiepunten (`todos`) en ingestuurde documenten (`docs`).
- `updates.json` + `updates/*.md`: de wekelijkse raadsupdates.
- `config.js`: `uploadUrl` = de /exec-URL van het Google-script.
- `apps-script/Code.gs`: script dat inzendingen in de Drive-inzendmap zet.

## Op het beginscherm zetten
- iPhone (Safari): deelknop › Zet op beginscherm.
- Android (Chrome): menu ⋮ › App installeren / Toevoegen aan startscherm.

## Google-script instellen (eenmalig)
1. Ga naar script.google.com › Nieuw project, met het account dat eigenaar is van de inzendmap.
2. Plak de inhoud van `apps-script/Code.gs` en vervang `VUL-HIER-EEN-CODE-IN` door een zelfgekozen fractiecode.
3. Implementeren › Nieuwe implementatie › type Web-app. Uitvoeren als: ik. Toegang: iedereen.
4. Geef toestemming, kopieer de URL die eindigt op `/exec` en zet die in `config.js`.

De fractiecode komt niet in deze repo; deel hem alleen binnen de fractie.
