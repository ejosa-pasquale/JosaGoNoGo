# eV Field Service — Streamlit GO/NO-GO (Light)

Questa app Streamlit:
- prende in input **N veicoli** e **km annui medi per veicolo**
- dimensiona una configurazione minima **AC** (o **DC** se la domanda per veicolo è molto alta)
- stima **CAPEX** come: `Σ (acq + ins) * q`
- calcola KPI:
  - **Δ costo energia vs diesel** (base, solo energia)
  - **Payback** (solo HW)
  - **CO₂ evitata**, **diesel evitato**, **alberi equivalenti**, **rating ESG (semplice)**

## Avvio
```bash
pip install -r requirements.txt
streamlit run app.py
```
