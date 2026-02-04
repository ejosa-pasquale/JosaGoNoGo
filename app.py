import streamlit as st
import pandas as pd
from math import ceil
from dataclasses import dataclass

st.set_page_config(page_title="eV Field Service | GO/NO-GO EV Fleet", page_icon="⚡", layout="wide")

@dataclass(frozen=True)
class Params:
    # Operatività (coerente con engine: finestra 09-19)
    charging_window_hours: float = 10.0

    # Rotazioni (default nel tuo engine)
    ac_rotation: int = 2
    dc_rotation: int = 6

    # Potenze effettive (nel motore AC viene limitata a 11 kW)
    ac_power_effective_kw: float = 11.0
    dc30_power_kw: float = 30.0
    dc60_power_kw: float = 60.0

    # Costi default (acq + ins)
    ac22_acq_eur: float = 1500.0
    ac22_ins_eur: float = 1600.0
    dc30_acq_eur: float = 8500.0
    dc30_ins_eur: float = 7500.0
    dc60_acq_eur: float = 16000.0
    dc60_ins_eur: float = 7500.0

    # Consumi / costi energia (default UI)
    ev_kwh_per_km: float = 0.22
    energy_internal_eur_per_kwh: float = 0.22

    # Diesel (default UI)
    diesel_km_per_l: float = 15.0
    diesel_eur_per_l: float = 1.75
    diesel_kgco2_per_l: float = 2.65

    # KPI ESG (come nel motore: trees = int(co2 * 50))
    trees_per_ton_co2: int = 50

    # Gate economico
    payback_threshold_years: float = 4.0

def estimate(N: int, km_per_vehicle_year: float, p: Params):
    # Domanda
    km_total_year = N * km_per_vehicle_year
    km_per_vehicle_day = km_per_vehicle_year / 365.0
    kwh_per_vehicle_day = km_per_vehicle_day * p.ev_kwh_per_km
    kwh_total_day = N * kwh_per_vehicle_day
    kwh_total_year = km_total_year * p.ev_kwh_per_km

    # Capacità giornaliera per punto
    kwh_ac_day = p.ac_power_effective_kw * p.charging_window_hours
    kwh_dc30_day = p.dc30_power_kw * p.charging_window_hours
    kwh_dc60_day = p.dc60_power_kw * p.charging_window_hours

    # Regola di scelta: se energia/auto/giorno > 55 kWh -> serve DC (AC: ~5h/auto con rotazione 2, 11kW => 55)
    needs_dc = kwh_per_vehicle_day > 55.0

    sizing = {}
    capex = 0.0

    if not needs_dc:
        q_ac_by_rotation = ceil(N / p.ac_rotation)
        q_ac_by_energy = ceil(kwh_total_day / kwh_ac_day) if kwh_total_day > 0 else 0
        q_ac = max(q_ac_by_rotation, q_ac_by_energy)

        capex = q_ac * (p.ac22_acq_eur + p.ac22_ins_eur)
        sizing = dict(
            hardware="AC 22kW (eff. 11kW)",
            q_ac=q_ac,
            q_ac_by_rotation=q_ac_by_rotation,
            q_ac_by_energy=q_ac_by_energy,
            kwh_per_station_day=kwh_ac_day,
        )
    else:
        # DC: scegliamo DC30 fino a 90 kWh/giorno per auto, altrimenti DC60
        use_dc60 = kwh_per_vehicle_day > 90.0
        if use_dc60:
            q_dc_by_rotation = ceil(N / p.dc_rotation)
            q_dc_by_energy = ceil(kwh_total_day / kwh_dc60_day) if kwh_total_day > 0 else 0
            q_dc = max(q_dc_by_rotation, q_dc_by_energy)
            capex = q_dc * (p.dc60_acq_eur + p.dc60_ins_eur)
            sizing = dict(
                hardware="DC 60kW",
                q_dc=q_dc,
                q_dc_by_rotation=q_dc_by_rotation,
                q_dc_by_energy=q_dc_by_energy,
                kwh_per_station_day=kwh_dc60_day,
            )
        else:
            q_dc_by_rotation = ceil(N / p.dc_rotation)
            q_dc_by_energy = ceil(kwh_total_day / kwh_dc30_day) if kwh_total_day > 0 else 0
            q_dc = max(q_dc_by_rotation, q_dc_by_energy)
            capex = q_dc * (p.dc30_acq_eur + p.dc30_ins_eur)
            sizing = dict(
                hardware="DC 30kW",
                q_dc=q_dc,
                q_dc_by_rotation=q_dc_by_rotation,
                q_dc_by_energy=q_dc_by_energy,
                kwh_per_station_day=kwh_dc30_day,
            )

    # KPI economici base (energia interna vs diesel)
    diesel_liters_year = km_total_year / p.diesel_km_per_l if p.diesel_km_per_l > 0 else 0.0
    diesel_cost_year = diesel_liters_year * p.diesel_eur_per_l
    ev_energy_cost_year = kwh_total_year * p.energy_internal_eur_per_kwh
    delta_fossil_year = diesel_cost_year - ev_energy_cost_year

    payback_years = (capex / delta_fossil_year) if delta_fossil_year > 0 else float("inf")
    go = (delta_fossil_year > 0) and (payback_years <= p.payback_threshold_years)

    # ESG KPI (coerente col motore: co2 in ton/anno, trees=int(co2*50))
    co2_avoided_tons_year = (diesel_liters_year * p.diesel_kgco2_per_l) / 1000.0
    trees_equivalent = int(co2_avoided_tons_year * p.trees_per_ton_co2)

    return {
        "inputs": {
            "N": N,
            "km_per_vehicle_year": km_per_vehicle_year,
            "km_total_year": km_total_year,
        },
        "energy": {
            "kwh_per_vehicle_day": kwh_per_vehicle_day,
            "kwh_total_day": kwh_total_day,
            "kwh_total_year": kwh_total_year,
        },
        "sizing": sizing,
        "capex": {"capex_eur": capex},
        "economics": {
            "diesel_cost_year_eur": diesel_cost_year,
            "ev_energy_cost_year_eur": ev_energy_cost_year,
            "delta_fossil_year_eur": delta_fossil_year,
            "payback_years_hw_only": payback_years,
            "decision": "GO" if go else "NO-GO",
        },
        "esg": {
            "diesel_avoided_liters_year": diesel_liters_year,
            "co2_avoided_tons_year": co2_avoided_tons_year,
            "trees_equivalent": trees_equivalent,
            "esg_rating": "AAA" if co2_avoided_tons_year >= 5 else ("A" if co2_avoided_tons_year >= 1 else "B"),
        }
    }

st.markdown("""
<style>
  .card {background:#ffffff; padding:16px; border-radius:14px; border:1px solid #E2E8F0;}
  .title {font-size:1.6rem; font-weight:800;}
  .sub {color:#475569;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="card"><div class="title">⚡ eV Field Service — GO/NO-GO Fleet Electrification</div><div class="sub">Sizing hardware + CAPEX (stile engine) + KPI economici + KPI ESG, usando solo N veicoli e km annui.</div></div>', unsafe_allow_html=True)
st.write("")

# Sidebar: parametri (tutti opzionali, ma con default coerenti)
st.sidebar.header("⚙️ Parametri (opzionali)")
p = Params(
    charging_window_hours=st.sidebar.number_input("Finestra ricarica (h)", 4.0, 16.0, 10.0, 0.5),
    ac_rotation=st.sidebar.number_input("Rotazione AC (auto/colonnina/giorno)", 1, 6, 2, 1),
    dc_rotation=st.sidebar.number_input("Rotazione DC (auto/colonnina/giorno)", 1, 20, 6, 1),
    ev_kwh_per_km=st.sidebar.number_input("Consumo EV (kWh/km)", 0.10, 0.80, 0.22, 0.01),
    energy_internal_eur_per_kwh=st.sidebar.number_input("Costo energia interna (€/kWh)", 0.05, 1.50, 0.22, 0.01),
    diesel_km_per_l=st.sidebar.number_input("Diesel (km/L)", 5.0, 30.0, 15.0, 0.5),
    diesel_eur_per_l=st.sidebar.number_input("Diesel (€/L)", 0.5, 3.5, 1.75, 0.01),
    payback_threshold_years=st.sidebar.number_input("Soglia Payback (anni)", 1.0, 10.0, 4.0, 0.5),
)

st.sidebar.divider()
st.sidebar.subheader("💸 Costi HW (default)")
st.sidebar.caption("Puoi allinearli ai vostri listini/parametri reali.")
p = Params(
    **{**p.__dict__,
       "ac22_acq_eur": st.sidebar.number_input("AC22 acquisto (€)", 0.0, 50000.0, 1500.0, 100.0),
       "ac22_ins_eur": st.sidebar.number_input("AC22 install (€)", 0.0, 50000.0, 1600.0, 100.0),
       "dc30_acq_eur": st.sidebar.number_input("DC30 acquisto (€)", 0.0, 200000.0, 8500.0, 250.0),
       "dc30_ins_eur": st.sidebar.number_input("DC30 install (€)", 0.0, 200000.0, 7500.0, 250.0),
       "dc60_acq_eur": st.sidebar.number_input("DC60 acquisto (€)", 0.0, 300000.0, 16000.0, 500.0),
       "dc60_ins_eur": st.sidebar.number_input("DC60 install (€)", 0.0, 300000.0, 7500.0, 500.0),
    }
)

col1, col2 = st.columns([1, 1])
with col1:
    st.markdown("### Input flotta")
    N = st.number_input("Numero veicoli (N)", min_value=1, max_value=5000, value=11, step=1)
    km = st.number_input("Km annui medi per veicolo", min_value=0, max_value=200000, value=30000, step=1000)
    run = st.button("Calcola", use_container_width=True)

with col2:
    st.markdown("### Esempi rapidi")
    if st.button("11 auto / 30.000 km", use_container_width=True):
        st.session_state["N"] = 11
        st.session_state["km"] = 30000
        run = True
    if st.button("8 auto / 20.000 km", use_container_width=True):
        st.session_state["N"] = 8
        st.session_state["km"] = 20000
        run = True

if "N" in st.session_state:
    N = st.session_state["N"]
if "km" in st.session_state:
    km = st.session_state["km"]

if run:
    res = estimate(int(N), float(km), p)

    decision = res["economics"]["decision"]
    if decision == "GO":
        st.success("✅ GO — investimento compatibile col ritorno (payback sotto soglia).")
    else:
        st.error("⛔ NO-GO — investimento non compatibile col ritorno (payback oltre soglia o saving ≤ 0).")

    # KPI cards
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Hardware stimato", res["sizing"]["hardware"])
    m2.metric("CAPEX stimato", f"€ {res['capex']['capex_eur']:,.0f}")
    pb = res["economics"]["payback_years_hw_only"]
    m3.metric("Payback (solo HW)", "∞" if pb == float("inf") else f"{pb:.2f} anni")
    m4.metric("Δ costo energia vs diesel", f"€ {res['economics']['delta_fossil_year_eur']:,.0f}/anno")

    st.write("")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("CO₂ evitata", f"{res['esg']['co2_avoided_tons_year']:.2f} t/anno")
    e2.metric("Diesel evitato", f"{res['esg']['diesel_avoided_liters_year']:,.0f} L/anno")
    e3.metric("Alberi equivalenti", f"🌲 {res['esg']['trees_equivalent']}")
    e4.metric("Rating ESG (semplice)", res["esg"]["esg_rating"])

    st.divider()
    st.markdown("### Dettaglio calcoli")
    left, right = st.columns(2)

    with left:
        st.markdown("**Energia**")
        st.json(res["energy"])
        st.markdown("**Sizing**")
        st.json(res["sizing"])

    with right:
        st.markdown("**Economics**")
        st.json(res["economics"])
        st.markdown("**ESG**")
        st.json(res["esg"])

    # Export
    st.divider()
    st.markdown("### Export")
    df = pd.DataFrame([{
        **res["inputs"],
        **{"kwh_total_year": res["energy"]["kwh_total_year"], "kwh_total_day": res["energy"]["kwh_total_day"]},
        **{"hardware": res["sizing"]["hardware"], "capex_eur": res["capex"]["capex_eur"]},
        **{"delta_fossil_year_eur": res["economics"]["delta_fossil_year_eur"], "payback_years_hw_only": pb, "decision": decision},
        **{"co2_avoided_tons_year": res["esg"]["co2_avoided_tons_year"], "diesel_avoided_liters_year": res["esg"]["diesel_avoided_liters_year"], "trees_equivalent": res["esg"]["trees_equivalent"], "esg_rating": res["esg"]["esg_rating"]},
    }])

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Scarica risultati (CSV)", data=csv, file_name="ev_go_nogo_results.csv", mime="text/csv", use_container_width=True)
