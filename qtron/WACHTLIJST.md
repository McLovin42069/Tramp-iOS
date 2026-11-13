# Qtron wachtlijst

## Nog open

1. **Optie- en kwartierdata toetsen** als het archief ongeveer 120 handelsdagen bevat (rond mei 2027): onderscheidt het vroege instroom die doorzet van instroom die omkeert?
2. **Patroon als extra gewicht in de analist** zodra een patroon de status LIVE BEVESTIGD haalt. Nu toont de analist het lidmaatschap alleen als aandachtspunt.
3. **Tweede koersbron naast Yahoo.** Onderzocht op 13-11-2026; kandidaten die een gratis sleutel van jou vragen: Tiingo (Amerikaanse dagkoersen, 500 symbolen per maand) en Alpaca (Amerikaanse kwartierkoersen, meerdere jaren terug). Zonder sleutel: ECB-wisselkoersen en Kraken als controle op valuta en crypto; Stooq-bestanden alleen met handmatige download. Voor Europese en Aziatische aandelen bestaat geen gratis bron die Yahoo evenaart.
4. **Sectorrang bij de waarderingscijfers** (vereist SEC-data op de pc; nu toont INSTRUMENT de cijfers van Yahoo zonder rang).

## Gebouwd op 13-11-2026

- Universum naar ruim 3.100 instrumenten: 1.033 Amerikaanse, 810 Europese en 1.161 Aziatische aandelen, 24 beursindices; maandelijkse automatische verversing. De patronen blijven op hun oorspronkelijke lijst rekenen.
- Marktalarm (groen, oranje, rood) in de Cockpit, de analist en bij orders.
- Agenda met rentebesluiten en winstcijfers; waarschuwing bij aankoop vlak voor cijfers.
- INSTRUMENT: koersniveaus en positiegrootte, waardering, nieuws.
- PORTEFEUILLE: risicoscherm met scenario's, positiegrootte op risico, kosten inclusief beurstaks en spread, dagboek, vergelijking met een wereldindex.
- Analist: aandachtspunten voor winstcijfers, goedkoop plus sterke instroom, en plaats in de Aziatische patronen.
- Meldingen op de telefoon via ntfy (standaard uit).
- Handleiding.
- Analist omgebouwd: gewichten volgen het bewijs, keuze op spreiding tegenover de portefeuille, geen voorstellen bij rood alarm. De oude regel loopt mee in het trackrecord (voorvoegsel OUD).

## Getoetst en afgewezen (niet opnieuw proberen zonder nieuwe data)

Uitkomsten staan in `money-flow-command-center/research5/`.

- Vroege instroom detecteren uit koers en volume (debiet, omslag, versnelling)
- Fase versnelt / stabiel / verzwakt binnen positieve instroom, 5 tot 60 dagen
- Aankopen en verkopen door bestuurders (SEC Form 4), los en als filter
- Kwartaalposities van fondsen (SEC 13F), los en als filter
- Waarde volgens de balans (Graham/Buffett), los en gecombineerd met geldstroom
- Marktalarm als rendementsbron: verkleint het grootste verlies, kost rendement
