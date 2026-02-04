import streamlit as st
import pandas as pd
from math import ceil
from dataclasses import dataclass

st.set_page_config(page_title="eV Field Service | GO/NO-GO", page_icon="⚡", layout="wide")

st.markdown("""
<style>
:root{
  --bg: #F7F8FB;
  --card: #FFFFFF;
  --text: #0F172A;
  --muted: #475569;
  --line: #E2E8F0;
  --brand1: #0EA5E9;
  --brand2: #10B981;
  --warn: #F59E0B;
  --bad: #EF4444;
  --good: #22C55E;
}
.stApp { background: var(--bg); color: var(--text); }
.block-container { padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1200px; }
.hero {
  background: linear-gradient(90deg, rgba(14,165,233,0.14) 0%, rgba(16,185,129,0.14) 100%);
  border: 1px solid rgba(226,232,240,1);
  border-radius: 18px;
  padding: 18px 18px 14px 18px;
}
.hero h1{ font-size: 1.55rem; line-height: 1.2; margin: 0; font-weight: 850; }
.hero p{ margin: 6px 0 0 0; color: var(--muted); font-size: 0.95rem; }
.badge {
  display:inline-block; padding: 4px 10px; border-radius: 999px; font-weight: 700; font-size: 0.78rem;
  border: 1px solid var(--line); background: rgba(255,255,255,0.85); color: #0f172a;
}
.card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 16px; }
.card h3{ margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 800; }
.subtle { color: var(--muted); font-size: 0.92rem; }
.pill{
  display:inline-flex; gap: 8px; align-items:center; padding: 7px 10px; border-radius: 999px;
  border: 1px solid var(--line); background: #fff; font-weight: 750; font-size: 0.9rem; margin-right: 8px; margin-bottom: 6px;
}
.pill.good{ border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.08); }
.pill.bad{ border-color: rgba(239,68,68,0.35); background: rgba(239,68,68,0.08); }
.pill.warn{ border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.08); }
.kpiRow { display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
@media (max-width: 1100px) { .kpiRow { grid-template-columns: repeat(2, 1fr); } }
.kpi { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 14px 14px 10px 14px; }
.kpi .label{ color: var(--muted); font-size: 0.83rem; margin-bottom: 2px;}
.kpi .value{ font-size: 1.15rem; font-weight: 900; }
.kpi .hint{ color: var(--muted); font-size: 0.78rem; margin-top: 4px; }
.hr { height: 1px; background: var(--line); margin: 10px 0 2px 0; }
.footer{ color: var(--muted); font-size: 0.85rem; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

@dataclass(frozen=True)
class Params:
    charging_window_hours: float = 10.0
    working_days: int = 240

    ac_rotation: int = 2
    dc_rotation: int = 6

    ac_power_effective_kw: float = 11.0
    dc30_power_kw: float = 30.0
    dc60_power_kw: float = 60.0

    ac22_acq_eur: float = 1500.0
    ac22_ins_eur: float = 1600.0
    dc30_acq_eur: float = 8500.0
    dc30_ins_eur: float = 7500.0
    dc60_acq_eur: float = 16000.0
    dc60_ins_eur: float = 7500.0

    ev_kwh_per_km: float = 0.22
    energy_internal_eur_per_kwh: float = 0.22

    diesel_km_per_l: float = 15.0
    diesel_eur_per_l: float = 1.75
    diesel_kgco2_per_l: float = 2.65

    trees_per_ton_co2: int = 50
    payback_threshold_years: float = 4.0

    peak_factor: float = 1.25


def estimate(N: int, km_per_vehicle_year: float, p: Params):
    km_total_year = N * km_per_vehicle_year
    kwh_total_year = km_total_year * p.ev_kwh_per_km

    # Giorno medio (su giorni lavorativi)
    km_per_vehicle_day = km_per_vehicle_year / float(p.working_days)
    kwh_per_vehicle_day = km_per_vehicle_day * p.ev_kwh_per_km

    kwh_total_day_avg = N * kwh_per_vehicle_day
    kwh_total_day_peak = kwh_total_day_avg * p.peak_factor

    kwh_ac_day = p.ac_power_effective_kw * p.charging_window_hours
    kwh_dc30_day = p.dc30_power_kw * p.charging_window_hours
    kwh_dc60_day = p.dc60_power_kw * p.charging_window_hours

    needs_dc = kwh_per_vehicle_day > 55.0

    if not needs_dc:
        q_by_rotation = ceil(N / p.ac_rotation)
        q_by_energy = ceil(kwh_total_day_peak / kwh_ac_day) if kwh_total_day_peak > 0 else 0
        q = max(q_by_rotation, q_by_energy)
        capex = q * (p.ac22_acq_eur + p.ac22_ins_eur)
        sizing = dict(hardware="AC 22kW (eff. 11kW)", points=q, by_rotation=q_by_rotation, by_energy=q_by_energy, kwh_per_station_day=kwh_ac_day)
    else:
        use_dc60 = kwh_per_vehicle_day > 90.0
        if use_dc60:
            q_by_rotation = ceil(N / p.dc_rotation)
            q_by_energy = ceil(kwh_total_day_peak / kwh_dc60_day) if kwh_total_day_peak > 0 else 0
            q = max(q_by_rotation, q_by_energy)
            capex = q * (p.dc60_acq_eur + p.dc60_ins_eur)
            sizing = dict(hardware="DC 60kW", points=q, by_rotation=q_by_rotation, by_energy=q_by_energy, kwh_per_station_day=kwh_dc60_day)
        else:
            q_by_rotation = ceil(N / p.dc_rotation)
            q_by_energy = ceil(kwh_total_day_peak / kwh_dc30_day) if kwh_total_day_peak > 0 else 0
            q = max(q_by_rotation, q_by_energy)
            capex = q * (p.dc30_acq_eur + p.dc30_ins_eur)
            sizing = dict(hardware="DC 30kW", points=q, by_rotation=q_by_rotation, by_energy=q_by_energy, kwh_per_station_day=kwh_dc30_day)

    # Economics (solo energia interna)
    diesel_liters_year = km_total_year / p.diesel_km_per_l if p.diesel_km_per_l > 0 else 0.0
    diesel_cost_year = diesel_liters_year * p.diesel_eur_per_l
    ev_energy_cost_year = kwh_total_year * p.energy_internal_eur_per_kwh
    delta_fossil_year = diesel_cost_year - ev_energy_cost_year

    payback_years = (capex / delta_fossil_year) if delta_fossil_year > 0 else float("inf")
    decision = "GO" if (delta_fossil_year > 0 and payback_years <= p.payback_threshold_years) else "NO-GO"

    # ESG KPIs (baseline diesel, in questa versione "light")
    co2_avoided_tons_year = (diesel_liters_year * p.diesel_kgco2_per_l) / 1000.0
    co2_avoided_kg_year = co2_avoided_tons_year * 1000.0
    co2_avoided_kg_per_vehicle_year = co2_avoided_kg_year / N
    co2_avoided_g_per_km = (co2_avoided_kg_year * 1000.0) / km_total_year if km_total_year > 0 else 0.0
    trees_equivalent = int(co2_avoided_tons_year * p.trees_per_ton_co2)

    if co2_avoided_tons_year >= 10:
        esg_rating = "AAA"
    elif co2_avoided_tons_year >= 3:
        esg_rating = "AA"
    elif co2_avoided_tons_year >= 1:
        esg_rating = "A"
    else:
        esg_rating = "B"

    return {
        "inputs": {"N": N, "km_per_vehicle_year": km_per_vehicle_year, "km_total_year": km_total_year},
        "energy": {
            "working_days": p.working_days,
            "kwh_per_vehicle_day": kwh_per_vehicle_day,
            "kwh_total_day_avg": kwh_total_day_avg,
            "kwh_total_day_peak": kwh_total_day_peak,
            "kwh_total_year": kwh_total_year,
        },
        "sizing": sizing,
        "capex": {"capex_eur": capex},
        "economics": {
            "diesel_cost_year_eur": diesel_cost_year,
            "ev_energy_cost_year_eur": ev_energy_cost_year,
            "delta_fossil_year_eur": delta_fossil_year,
            "payback_years_hw_only": payback_years,
            "decision": decision,
        },
        "esg": {
            "diesel_avoided_liters_year": diesel_liters_year,
            "co2_avoided_tons_year": co2_avoided_tons_year,
            "co2_avoided_kg_per_vehicle_year": co2_avoided_kg_per_vehicle_year,
            "co2_avoided_g_per_km": co2_avoided_g_per_km,
            "trees_equivalent": trees_equivalent,
            "esg_rating": esg_rating,
        },
    }


st.markdown("""
<div class="hero">
  <div class="badge">⚡ GO/NO-GO — Fleet Electrification</div>
  <h1>Decisione rapida, numeri solidi</h1>
  <p>Inserisci <b>N veicoli</b> e <b>km annui</b>. Dimensioniamo per giorni di picco e stimiamo CAPEX, payback e KPI ESG.</p>
</div>
""", unsafe_allow_html=True)
st.write("")

with st.sidebar:
    st.header("🧩 Impostazioni")
    st.caption("Per una demo semplice, lascia i default. Apri *Avanzate* solo se vuoi rifinire le assunzioni.")
    with st.expander("Avanzate (assunzioni & costi)", expanded=False):
        colA, colB = st.columns(2)
        with colA:
            st.number_input("Finestra ricarica (h)", 4.0, 16.0, 10.0, 0.5, key="Finestra ricarica (h)")
            st.number_input("Giorni lavorativi/anno", 200, 365, 240, 5, key="Giorni lavorativi/anno")
            st.number_input("Rotazione AC (auto/punto/g)", 1, 6, 2, 1, key="Rotazione AC (auto/punto/g)")
            st.number_input("Rotazione DC (auto/punto/g)", 1, 20, 6, 1, key="Rotazione DC (auto/punto/g)")
            st.number_input("Consumo EV (kWh/km)", 0.10, 0.80, 0.22, 0.01, key="Consumo EV (kWh/km)")
            st.number_input("Energia interna (€/kWh)", 0.05, 1.50, 0.22, 0.01, key="Energia interna (€/kWh)")
        with colB:
            st.number_input("Diesel (km/L)", 5.0, 30.0, 15.0, 0.5, key="Diesel (km/L)")
            st.number_input("Diesel (€/L)", 0.5, 3.5, 1.75, 0.01, key="Diesel (€/L)")
            st.number_input("Soglia payback (anni)", 1.0, 10.0, 4.0, 0.5, key="Soglia payback (anni)")
            st.number_input("Peak factor (× domanda gg)", 1.0, 2.0, 1.25, 0.05, key="Peak factor (× domanda gg)")
            st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
            st.caption("Costi hardware (acquisto + installazione)")
            st.number_input("AC22 acquisto (€)", 0.0, 50000.0, 1500.0, 100.0, key="AC22 acquisto (€)")
            st.number_input("AC22 install (€)", 0.0, 50000.0, 1600.0, 100.0, key="AC22 install (€)")
            st.number_input("DC30 acquisto (€)", 0.0, 200000.0, 8500.0, 250.0, key="DC30 acquisto (€)")
            st.number_input("DC30 install (€)", 0.0, 200000.0, 7500.0, 250.0, key="DC30 install (€)")
            st.number_input("DC60 acquisto (€)", 0.0, 300000.0, 16000.0, 500.0, key="DC60 acquisto (€)")
            st.number_input("DC60 install (€)", 0.0, 300000.0, 7500.0, 500.0, key="DC60 install (€)")

    st.markdown("<div class='hr'></div>", unsafe_allow_html=True)
    st.markdown("**Suggerimento:** per un pitch, mostra GO/NO‑GO + CAPEX + Payback + CO₂ evitata.")
    st.markdown("<div class='footer'>© eV Field Service • Data-driven fleet electrification</div>", unsafe_allow_html=True)

def _get(label: str, default):
    return st.session_state.get(label, default)

p = Params(
    charging_window_hours=_get("Finestra ricarica (h)", 10.0),
    working_days=_get("Giorni lavorativi/anno", 240),
    ac_rotation=_get("Rotazione AC (auto/punto/g)", 2),
    dc_rotation=_get("Rotazione DC (auto/punto/g)", 6),
    ev_kwh_per_km=_get("Consumo EV (kWh/km)", 0.22),
    energy_internal_eur_per_kwh=_get("Energia interna (€/kWh)", 0.22),
    diesel_km_per_l=_get("Diesel (km/L)", 15.0),
    diesel_eur_per_l=_get("Diesel (€/L)", 1.75),
    payback_threshold_years=_get("Soglia payback (anni)", 4.0),
    peak_factor=_get("Peak factor (× domanda gg)", 1.25),
    ac22_acq_eur=_get("AC22 acquisto (€)", 1500.0),
    ac22_ins_eur=_get("AC22 install (€)", 1600.0),
    dc30_acq_eur=_get("DC30 acquisto (€)", 8500.0),
    dc30_ins_eur=_get("DC30 install (€)", 7500.0),
    dc60_acq_eur=_get("DC60 acquisto (€)", 16000.0),
    dc60_ins_eur=_get("DC60 install (€)", 7500.0),
)

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("<div class='card'><h3>1) Inserisci i dati minimi</h3><div class='subtle'>Solo 2 variabili: semplicissimo per qualsiasi azienda.</div></div>", unsafe_allow_html=True)
    st.write("")
    N = st.number_input("Numero veicoli (N)", min_value=1, max_value=5000, value=int(st.session_state.get("N", 11)), step=1)
    km = st.number_input("Km annui medi per veicolo", min_value=0, max_value=200000, value=int(st.session_state.get("km", 30000)), step=1000)

    c1, c2 = st.columns(2)
    with c1:
        run = st.button("Calcola GO/NO‑GO ⚡", use_container_width=True)
    with c2:
        reset = st.button("Reset", use_container_width=True)
        if reset:
            for k in ["N", "km", "last_result"]:
                st.session_state.pop(k, None)
            st.rerun()

    st.write("")
    st.markdown("<div class='card'><h3>Esempi rapidi</h3><div class='subtle'>Carica uno scenario tipico in un click.</div></div>", unsafe_allow_html=True)
    ex1, ex2 = st.columns(2)
    with ex1:
        if st.button("11 auto • 30.000 km", use_container_width=True):
            st.session_state["N"] = 11
            st.session_state["km"] = 30000
            st.session_state["last_result"] = estimate(11, 30000.0, p)
    with ex2:
        if st.button("8 auto • 20.000 km", use_container_width=True):
            st.session_state["N"] = 8
            st.session_state["km"] = 20000
            st.session_state["last_result"] = estimate(8, 20000.0, p)

with right:
    st.markdown("<div class='card'><h3>2) Risultato</h3><div class='subtle'>Decisione + KPI chiave (economics + ESG). Peak e giorni lavorativi sempre visibili.</div></div>", unsafe_allow_html=True)
    st.write("")

    if run:
        st.session_state["N"] = int(N)
        st.session_state["km"] = int(km)
        st.session_state["last_result"] = estimate(int(N), float(km), p)

    res = st.session_state.get("last_result")

    if not res:
        st.info("Inserisci i dati e premi **Calcola**. Qui comparirà la decisione GO/NO‑GO con i KPI.")
    else:
        decision = res["economics"]["decision"]
        pb = res["economics"]["payback_years_hw_only"]
        capex = res["capex"]["capex_eur"]

        if decision == "GO":
            st.markdown("<div class='pill good'>✅ GO <span class='subtle'>investimento compatibile con il ritorno</span></div>", unsafe_allow_html=True)
        else:
            st.markdown("<div class='pill bad'>⛔ NO‑GO <span class='subtle'>investimento non compatibile con il ritorno</span></div>", unsafe_allow_html=True)

        st.markdown(f"<div class='pill warn'>⚡ Peak-ready +{int((p.peak_factor-1)*100)}% (factor {p.peak_factor:.2f})</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='pill warn'>📅 {p.working_days} giorni lavorativi/anno</div>", unsafe_allow_html=True)

        def fmt_eur(x): return f"€ {x:,.0f}"
        def fmt_years(x): return "∞" if x == float("inf") else f"{x:.2f} anni"

        st.write("")
        st.markdown("<div class='kpiRow'>", unsafe_allow_html=True)
        st.markdown(f"""
          <div class="kpi">
            <div class="label">Hardware stimato</div>
            <div class="value">{res["sizing"]["hardware"]}</div>
            <div class="hint">{res["sizing"]["points"]} punti (minimo)</div>
          </div>
          <div class="kpi">
            <div class="label">CAPEX stimato</div>
            <div class="value">{fmt_eur(capex)}</div>
            <div class="hint">acquisto + installazione</div>
          </div>
          <div class="kpi">
            <div class="label">Payback (solo HW)</div>
            <div class="value">{fmt_years(pb)}</div>
            <div class="hint">soglia: {p.payback_threshold_years:.1f} anni</div>
          </div>
          <div class="kpi">
            <div class="label">Δ costo energia vs diesel</div>
            <div class="value">{fmt_eur(res["economics"]["delta_fossil_year_eur"])}/anno</div>
            <div class="hint">solo energia (no leasing/mnt)</div>
          </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        st.markdown("<div class='kpiRow'>", unsafe_allow_html=True)
        st.markdown(f"""
          <div class="kpi">
            <div class="label">CO₂ evitata</div>
            <div class="value">{res["esg"]["co2_avoided_tons_year"]:.2f} t/anno</div>
            <div class="hint">baseline diesel</div>
          </div>
          <div class="kpi">
            <div class="label">CO₂ evitata / veicolo</div>
            <div class="value">{res["esg"]["co2_avoided_kg_per_vehicle_year"]:.0f} kg/anno</div>
            <div class="hint">media per veicolo</div>
          </div>
          <div class="kpi">
            <div class="label">CO₂ evitata / km</div>
            <div class="value">{res["esg"]["co2_avoided_g_per_km"]:.0f} g/km</div>
            <div class="hint">intensity</div>
          </div>
          <div class="kpi">
            <div class="label">Alberi equivalenti</div>
            <div class="value">🌲 {res["esg"]["trees_equivalent"]}</div>
            <div class="hint">metrica comunicativa</div>
          </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        st.markdown("<div class='kpiRow'>", unsafe_allow_html=True)
        st.markdown(f"""
          <div class="kpi">
            <div class="label">Domanda (media)</div>
            <div class="value">{res["energy"]["kwh_total_day_avg"]:.1f} kWh/g</div>
            <div class="hint">su {p.working_days} gg</div>
          </div>
          <div class="kpi">
            <div class="label">Domanda (picco)</div>
            <div class="value">{res["energy"]["kwh_total_day_peak"]:.1f} kWh/g</div>
            <div class="hint">media × peak</div>
          </div>
          <div class="kpi">
            <div class="label">Diesel evitato</div>
            <div class="value">{res["esg"]["diesel_avoided_liters_year"]:,.0f} L/anno</div>
            <div class="hint">stima</div>
          </div>
          <div class="kpi">
            <div class="label">Rating ESG</div>
            <div class="value">{res["esg"]["esg_rating"]}</div>
            <div class="hint">demo</div>
          </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.write("")
        tab1, tab2, tab3 = st.tabs(["📌 Dettaglio", "📤 Export", "ℹ️ Metodo"])
        with tab1:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Energia**")
                st.json(res["energy"])
                st.markdown("**Sizing**")
                st.json(res["sizing"])
            with c2:
                st.markdown("**Economics**")
                st.json(res["economics"])
                st.markdown("**ESG**")
                st.json(res["esg"])

        with tab2:
            df = pd.DataFrame([{
                **res["inputs"],
                "working_days": p.working_days,
                "peak_factor": p.peak_factor,
                "kwh_total_day_avg": res["energy"]["kwh_total_day_avg"],
                "kwh_total_day_peak": res["energy"]["kwh_total_day_peak"],
                "kwh_total_year": res["energy"]["kwh_total_year"],
                "hardware": res["sizing"]["hardware"],
                "points": res["sizing"]["points"],
                "capex_eur": res["capex"]["capex_eur"],
                "delta_fossil_year_eur": res["economics"]["delta_fossil_year_eur"],
                "payback_years_hw_only": pb,
                "decision": decision,
                "co2_avoided_tons_year": res["esg"]["co2_avoided_tons_year"],
                "co2_avoided_kg_per_vehicle_year": res["esg"]["co2_avoided_kg_per_vehicle_year"],
                "co2_avoided_g_per_km": res["esg"]["co2_avoided_g_per_km"],
                "diesel_avoided_liters_year": res["esg"]["diesel_avoided_liters_year"],
                "trees_equivalent": res["esg"]["trees_equivalent"],
                "esg_rating": res["esg"]["esg_rating"],
            }])
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Scarica risultati (CSV)", data=csv, file_name="ev_go_nogo_results.csv", mime="text/csv", use_container_width=True)

        with tab3:
            st.markdown("""
**Metodo:**
- Domanda media = `KM / giorni_lavorativi × consumo × N` (default **240 gg**)
- Domanda picco = `media × peak factor` (default **1.25**)
- Dimensionamento punti: `max(rotazione, energia su picco)`
- CAPEX = (acquisto + installazione) × punti
- ESG: CO₂ evitata (totale / veicolo / km), diesel evitato, alberi equivalenti.

> Economico: “solo energia” (no leasing/manutenzione).
""")

st.markdown("<div class='footer'>Tip: per un pitch, screenshot + CSV export → allegato perfetto.</div>", unsafe_allow_html=True)
