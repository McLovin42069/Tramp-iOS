# Qtron wachtlijst

Aanpassingen die afgesproken zijn maar nog niet gebouwd. Volgorde is geen prioriteit.

1. **Waarderingscijfers in het scherm INSTRUMENT.** Boekwaarde, winst en vrije kasstroom tegenover beurswaarde, schuld, rendement op eigen vermogen en de rang binnen de sector, uit SEC-jaarverslagen. Alleen informatief; geen invloed op de analist. Vereist dat het SEC-contactadres op de pc is ingesteld (omgevingsvariabele `QTRON_SEC_EMAIL`). Alleen Amerikaanse aandelen.
2. **Handleiding** schrijven zodra de definitieve versie vaststaat.
3. **Patronen aan de analist koppelen** zodra een patroon de status LIVE BEVESTIGD haalt.
4. **Optie- en kwartierdata toetsen** als het archief ongeveer 120 handelsdagen bevat (rond mei 2027): onderscheidt het vroege instroom die doorzet van instroom die omkeert?
5. **Universum automatisch verversen** (nu handmatig met `python build_universe.py`), en dezelfde uitbreiding voor Europa en Azië.

## Al gebouwd, wacht op jouw akkoord om te installeren

- **Universum naar 1.540 instrumenten** (1.028 Amerikaanse aandelen, SpaceX, 24 beursindices; nieuwe noteringen tellen mee na 80 dagen). Zit in de laatste installer. Niet installeren = alles blijft zoals het was.

## Getoetst en afgewezen (niet opnieuw proberen zonder nieuwe data)

Uitkomsten staan in `money-flow-command-center/research5/`.

- Vroege instroom detecteren uit koers en volume (debiet, omslag, versnelling)
- Fase versnelt / stabiel / verzwakt binnen positieve instroom, 5 tot 60 dagen
- Aankopen en verkopen door bestuurders (SEC Form 4), los en als filter
- Kwartaalposities van fondsen (SEC 13F), los en als filter
- Waarde volgens de balans (Graham/Buffett), los en gecombineerd met geldstroom
