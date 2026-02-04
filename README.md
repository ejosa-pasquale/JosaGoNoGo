# eV Field Service — Streamlit GO/NO-GO (Peak Visible)

App Streamlit per demo commerciali e pre-valutazioni:
- input minimo: **N veicoli** + **km annui medi**
- output immediato: **GO/NO‑GO**, sizing hardware, CAPEX, payback (solo HW), KPI ESG
- dimensionamento **sempre su picco**: domanda media × **peak factor** (default 1.25)
- peak factor è **visibile** nel risultato (badge + KPI domanda media/picco)

## Avvio
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Docker (opzionale)
```bash
docker build -t ev-go-nogo .
docker run -p 8501:8501 ev-go-nogo
```
