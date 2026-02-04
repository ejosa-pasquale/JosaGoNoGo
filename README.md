# eV Field Service — Streamlit GO/NO-GO (Peak + ESG + 240 gg)

- Input minimo: **N veicoli** + **km annui medi**
- Dimensionamento su **giorno di picco**: media × peak factor (default 1.25)
- Domanda giornaliera calcolata su **240 giorni lavorativi** (default)
- KPI ESG estesi:
  - CO₂ evitata (t/anno)
  - CO₂ evitata per veicolo (kg/anno)
  - CO₂ evitata per km (g/km)
  - Diesel evitato (L/anno)
  - Alberi equivalenti
  - Rating ESG (demo)

## Avvio
```bash
pip install -r requirements.txt
streamlit run app.py
```
