# eV Field Service — Streamlit GO/NO-GO (UX friendly)

App Streamlit pensata per demo **commerciali** e pre‑valutazioni:
- input minimo: **N veicoli** + **km annui medi**
- output immediato: **GO/NO‑GO**, sizing hardware, CAPEX, payback (solo HW), KPI ESG

## Avvio
```bash
pip install -r requirements.txt
streamlit run app.py
```

## UX
- Sidebar con **Avanzate** chiuse di default
- KPI in card, testo “da board”
- Export CSV pronto per email/report

## Deploy (opzionale)
```bash
docker build -t ev-go-nogo .
docker run -p 8501:8501 ev-go-nogo
```
