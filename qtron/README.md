# Qtron

Geldstromen, patronen en een eigen data-archief, volledig op gratis publieke data. Draait lokaal op één pc.

- `app.py` — de terminal (Streamlit): COCKPIT, GELDSTROMEN, INSTRUMENT, PATRONEN, ONDERZOEK, PORTEFEUILLE, ARCHIEF
- `patterns.py` — de zeven vaste regels uit het onderzoek, met kosten, en het kerkhof van verdwenen patronen
- `collector.py` — nachtelijke verzamelaar: legt signalen en rendementen vast (live-toets) en archiveert kwartierkoersen, optiemarkt, nieuwskoppen en crypto-rente
- `alarm.py`, `risk.py` — marktalarm en risicoberekeningen
- `store.py`, `feeds.py`, `universe.py`, `build_universe.py` — opslag, databronnen, ruim 3.100 instrumenten

Installeren op Linux: `bash install-qtron.sh`. Handmatig: `pip install -r requirements.txt && streamlit run app.py`.

Geen enkele regel is statistisch bewezen op ongeziene data. Geen beleggingsadvies.
