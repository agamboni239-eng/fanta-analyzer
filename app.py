import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Fanta Analyzer & Asta Live", page_icon="⚽", layout="wide"
)

# ---------------------------------------------------------
# INIZIALIZZAZIONE SESSION STATE PER ASTA LIVE
# ---------------------------------------------------------
if "asta_history" not in st.session_state:
    st.session_state["asta_history"] = []

if "df_data" not in st.session_state:
    st.session_state["df_data"] = None

st.title("⚽ Fanta Analyzer - Dashboard, Asta Live & Simulatore")

# 1. Sidebar: Caricamento File e Impostazioni Asta
st.sidebar.header("📁 1. Carica Listone / File Lega")
uploaded_file = st.sidebar.file_uploader(
    "Carica file Excel (.xlsx) o CSV (Export Fantaleghe)", type=["xlsx", "csv"]
)

if uploaded_file is not None and st.session_state["df_data"] is None:
    try:
        if uploaded_file.name.endswith(".csv"):
            try:
                df_raw = pd.read_csv(uploaded_file)
                if len(df_raw.columns) <= 1:
                    uploaded_file.seek(0)
                    df_raw = pd.read_csv(uploaded_file, sep=";")
            except Exception:
                uploaded_file.seek(0)
                df_raw = pd.read_csv(uploaded_file, sep=";")
        else:
            xls = pd.ExcelFile(uploaded_file)
            sheet = (
                "Tutti"
                if "Tutti" in xls.sheet_names
                else ("Lista calciatori" if "Lista calciatori" in xls.sheet_names else xls.sheet_names[0])
            )
            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)

        # Mappatura specifica per export e listone Leghe Fantacalcio
        mappatura = {
            "R": "Ruolo",
            "RM": "Ruolo Mantra",
            "Nome": "Calciatore",
            "Squadra": "Squadra",
            "Sq.": "Squadra",
            "Qt. A": "Quotazione",
            "Qt. A.": "Quotazione",
            "Qt. I": "Quotazione Iniziale",
            "QUOT.": "Quotazione",
            "FVM": "FVM",
            "FVM/1000": "FVM",
            "FM": "FantaMedia",
            "MV": "MediaVoto",
            "PGv": "PartiteVoto",
            "Pg": "PartiteVoto",
            "Info": "Status",
            "Note": "Status",
            "Indisponibili": "Status",
            "Stato": "Status",
        }
        df_raw = df_raw.rename(columns=mappatura)

        # Normalizzazione e inizializzazione colonna Status
        if "Status" not in df_raw.columns:
            df_raw["Status"] = "Disponibile"
        else:
            df_raw["Status"] = df_raw["Status"].fillna("Disponibile").astype(str)
            df_raw["Status"] = df_raw["Status"].replace(["", "-", "nan", "None"], "Disponibile")

        # Assicuriamo colonne minime per l'Asta
        if "FantaSquadra" not in df_raw.columns:
            df_raw["FantaSquadra"] = None
        if "Costo" not in df_raw.columns:
            df_raw["Costo"] = 0

        st.session_state["df_data"] = df_raw
        st.sidebar.success(f"File caricato! ({len(df_raw)} calciatori)")
    except Exception as e:
        st.sidebar.error(f"Errore caricamento: {e}")

df = st.session_state["df_data"]

# Funzioni ausiliarie per il Simulatore
def calcola_gol(punti, soglia_primo_gol=66.0, passo_gol=6.0):
    if punti < soglia_primo_gol:
        return 0
    return int((punti - soglia_primo_gol) // passo_gol) + 1

def calcola_miglior_xi(df_squadra, modulo=(3, 4, 3)):
    d_c, c_c, a_c = modulo
    df_temp = df_squadra.copy()
    df_temp["FM_clean"] = pd.to_numeric(df_temp["FantaMedia"], errors="coerce").fillna(6.0)
    
    p = df_temp[df_temp["Ruolo"] == "P"].nlargest(1, "FM_clean")
    d = df_temp[df_temp["Ruolo"] == "D"].nlargest(d_c, "FM_clean")
    c = df_temp[df_temp["Ruolo"] == "C"].nlargest(c_c, "FM_clean")
    a = df_temp[df_temp["Ruolo"] == "A"].nlargest(a_c, "FM_clean")
    
    if len(p) < 1 or len(d) < d_c or len(c) < c_c or len(a) < a_c:
        return None
    return pd.concat([p, d, c, a])

if df is not None:
    st.sidebar.write("---")
    st.sidebar.header("⚙️ 2. Impostazioni Asta Live")

    budget_iniziale = st.sidebar.number_input(
        "Budget Iniziale (Crediti)", min_value=100, max_value=2000, value=500
    )

    # Slot Rosa Target
    col_s1, col_s2 = st.sidebar.columns(2)
    target_P = col_s1.number_input("Slot P", value=3, min_value=1)
    target_D = col_s2.number_input("Slot D", value=8, min_value=1)
    target_C = col_s1.number_input("Slot C", value=8, min_value=1)
    target_A = col_s2.number_input("Slot A", value=6, min_value=1)
    target_slots = {"P": target_P, "D": target_D, "C": target_C, "A": target_A}
    tot_slots_target = sum(target_slots.values())

    # Configurazione FantaSquadre Partecipanti
    fantasquadre_esistenti = sorted([
        str(x)
        for x in df["FantaSquadra"].dropna().unique()
        if str(x).strip() != ""
    ])
    if not fantasquadre_esistenti:
        fantasquadre_esistenti = [f"FantaSquadra {i}" for i in range(1, 9)]

    fantasquadre_input = st.sidebar.text_area(
        "Lista FantaSquadre (una per riga):",
        value="\n".join(fantasquadre_esistenti),
        height=120,
    )
    lista_squadre = [
        s.strip() for s in fantasquadre_input.strip().split("\n") if s.strip()
    ]

    st.sidebar.write("---")
    st.sidebar.header("🔍 3. Filtri Generali")

    df_filtrato = df.copy()

    # Toggle esclusione infortunati / squalificati
    if "Status" in df_filtrato.columns:
        escludi_indisponibili = st.sidebar.checkbox("Escludi Infortunati e Squalificati", value=False)
        if escludi_indisponibili:
            parole_chiave = ["inf", "squalific", "fuori", "cedut"]
            pattern = "|".join(parole_chiave)
            df_filtrato = df_filtrato[
                ~df_filtrato["Status"].astype(str).str.lower().str.contains(pattern, regex=True)
            ]

    stato_opzioni = ["Tutti", "Solo Svincolati", "Solo Acquistati"]
    stato_sel = st.sidebar.selectbox("Stato Calciatore", stato_opzioni)

    if stato_sel == "Solo Svincolati":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].isna()
            | (df_filtrato["FantaSquadra"] == "")
        ]
    elif stato_sel == "Solo Acquistati":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].notna() & (df_filtrato["FantaSquadra"] != "")
        ]

    fantasquadre_filtro = ["Tutte"] + lista_squadre
    fantasquadra_sel = st.sidebar.selectbox(
        "FantaSquadra da Filtrare", fantasquadre_filtro
    )
    if fantasquadra_sel != "Tutte":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].astype(str) == fantasquadra_sel
        ]

    if "Ruolo" in df.columns:
        ruoli = ["Tutti"] + list(df["Ruolo"].dropna().astype(str).unique())
        ruolo_sel = st.sidebar.selectbox("Ruolo Classic", ruoli)
        if ruolo_sel != "Tutti":
            df_filtrato = df_filtrato[df_filtrato["Ruolo"].astype(str) == ruolo_sel]

    if "Calciatore" in df.columns:
        nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")
        if nome_cercato:
            df_filtrato = df_filtrato[
                df_filtrato["Calciatore"]
                .astype(str)
                .str.contains(nome_cercato, case=False)
            ]

    # TAB APPLICAZIONE
    tab_asta, tab1, tab2, tab3, tab4, tab5, tab_sim = st.tabs([
        "⚡ Assistente Asta Live",
        "📋 Lista Calciatori",
        "📊 Grafico Occasioni",
        "🛡️ Analisi Rose Lega",
        "🔄 Valutatore Scambi",
        "📄 Report & Formazione",
        "⚔️ Simulatore Scontri Diretti",
    ])

    # ---------------------------------------------------------
    # TAB ASTA LIVE
    # ---------------------------------------------------------
    with tab_asta:
        st.subheader("⚡ Chiamata & Chiusura Asta in Tempo Reale")

        col_chiamata, col_target = st.columns([1.2, 1])

        with col_chiamata:
            st.markdown("### 🏷️ Registra Acquisto")

            # Selezione giocatore svincolato
            svincolati_df = df[
                df["FantaSquadra"].isna() | (df["FantaSquadra"] == "")
            ].sort_values(by="FVM" if "FVM" in df.columns else "Calciatore", ascending=False)
            opzioni_giocatori = svincolati_df["Calciatore"].tolist()

            if opzioni_giocatori:
                giocatore_chiamato = st.selectbox(
                    "Seleziona Calciatore:", opzioni_giocatori
                )
                info_g = df[df["Calciatore"] == giocatore_chiamato].iloc[0]

                sq_acquirente = st.selectbox("Acquistato da:", lista_squadre)
                prezzo_acquisto = st.number_input(
                    "Prezzo di Aggiudicazione (Crediti):",
                    min_value=1,
                    max_value=budget_iniziale,
                    value=1,
                )

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("✅ Registra Acquisto", use_container_width=True):
                        idx = df[df["Calciatore"] == giocatore_chiamato].index[0]
                        st.session_state["df_data"].loc[idx, "FantaSquadra"] = sq_acquirente
                        st.session_state["df_data"].loc[idx, "Costo"] = prezzo_acquisto
                        st.session_state["asta_history"].append(
                            (giocatore_chiamato, sq_acquirente, prezzo_acquisto)
                        )
                        st.success(
                            f"Aggiudicato **{giocatore_chiamato}** a **{sq_acquirente}** per **{prezzo_acquisto} cr**!"
                        )
                        st.rerun()

                with c_btn2:
                    if (
                        st.button("↩️ Annulla Ultimo Acquisto", use_container_width=True)
                        and st.session_state["asta_history"]
                    ):
                        g_last, sq_last, p_last = st.session_state["asta_history"].pop()
                        idx = df[df["Calciatore"] == g_last].index[0]
                        st.session_state["df_data"].loc[idx, "FantaSquadra"] = None
                        st.session_state["df_data"].loc[idx, "Costo"] = 0
                        st.warning(f"Annullato acquisto di {g_last}.")
                        st.rerun()
            else:
                st.info("Tutti i calciatori sono stati acquistati!")

        with col_target:
            st.markdown("### 🎯 Moneyball Target: Prezzo Max Consigliato")
            if opzioni_giocatori and 'info_g' in locals():
                ruolo_g = info_g.get("Ruolo", "A")
                status_txt = str(info_g.get("Status", "Disponibile"))
                fvm_g = float(info_g.get("FVM", 0)) if pd.notna(info_g.get("FVM")) else 0
                fm_g = float(info_g.get("FantaMedia", 0)) if pd.notna(info_g.get("FantaMedia")) else 0

                status_lower = status_txt.lower()
                if any(k in status_lower for k in ["inf", "infortunat", "operat", "lesion"]):
                    badge_status = f"🚑 **{status_txt}**"
                elif any(k in status_lower for k in ["squalific", "sqv"]):
                    badge_status = f"🟥 **{status_txt}**"
                elif any(k in status_lower for k in ["dubbi", "ballottag", "rischi"]):
                    badge_status = f"⚠️ **{status_txt}**"
                elif any(k in status_lower for k in ["fuori", "cedut", "svincol", "esclus"]):
                    badge_status = f"🚫 **{status_txt}**"
                else:
                    badge_status = f"🟢 **{status_txt}**"

                df_sq_acq = df[df["FantaSquadra"] == sq_acquirente]
                spesi_acq = df_sq_acq["Costo"].sum()
                rimasti_acq = budget_iniziale - spesi_acq

                presi_ruolo = len(df_sq_acq[df_sq_acq["Ruolo"] == ruolo_g])
                slot_rimasti_ruolo = max(1, target_slots.get(ruolo_g, 6) - presi_ruolo)
                tot_slot_rimasti = max(1, tot_slots_target - len(df_sq_acq))

                fvm_scale = 1000.0 if fvm_g > 0 else 1.0
                budget_target_ruolo = rimasti_acq * (fvm_g / fvm_scale) * 1.6
                max_bid_possibile = rimasti_acq - (tot_slot_rimasti - 1)
                prezzo_max_consigliato = max(
                    1, min(int(round(budget_target_ruolo)), max_bid_possibile)
                )

                st.metric(
                    label=f"Prezzo Max Consigliato per {info_g['Calciatore']}",
                    value=f"{prezzo_max_consigliato} cr",
                    delta=f"Slot {ruolo_g} Rimanenti: {slot_rimasti_ruolo}",
                )

                st.write(f"**Ruolo:** `{ruolo_g}` | **Squadra:** `{info_g.get('Squadra', '-')}`")
                st.write(f"**Condizione:** {badge_status}")
                st.write(f"**FVM:** `{int(fvm_g)}` | **FantaMedia:** `{fm_g:.2f}`")
                st.write(f"**Crediti Residui ({sq_acquirente}):** `{rimasti_acq} cr`")
                st.write(f"**Max Offerta Singola consentita:** `{max_bid_possibile} cr`")

    st.write("---")

    # Tabella Riepilogativa Rose & Crediti
    st.markdown("### 📊 Monitor Crediti e Slot Rose Lega")

    report_rose = []
    for sq in lista_squadre:
        df_sq = df[df["FantaSquadra"] == sq]
        spesi = df_sq["Costo"].sum()
        residui = budget_iniziale - spesi

        p_count = len(df_sq[df_sq["Ruolo"] == "P"])
        d_count = len(df_sq[df_sq["Ruolo"] == "D"])
        c_count = len(df_sq[df_sq["Ruolo"] == "C"])
        a_count = len(df_sq[df_sq["Ruolo"] == "A"])
        tot_in_rosa = len(df_sq)

        slot_rimasti_tot = max(0, tot_slots_target - tot_in_rosa)
        max_bid = residui - (slot_rimasti_tot - 1) if slot_rimasti_tot > 0 else 0

        report_rose.append({
            "FantaSquadra": sq,
            "Crediti Spesi": spesi,
            "Crediti Residui": residui,
            "Max Offerta": max(0, max_bid),
            "P": f"{p_count}/{target_P}",
            "D": f"{d_count}/{target_D}",
            "C": f"{c_count}/{target_C}",
            "A": f"{a_count}/{target_A}",
            "Totale Rosa": f"{tot_in_rosa}/{tot_slots_target}",
        })

    df_report_rose = pd.DataFrame(report_rose)
    st.dataframe(df_report_rose, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------
    # TAB 1: LISTA GENERALE
    # ---------------------------------------------------------
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calciatori Selezionati", len(df_filtrato))

        if "FantaMedia" in df_filtrato.columns:
            max_fm = df_filtrato["FantaMedia"].max() if not df_filtrato.empty else 0
            col2.metric("FantaMedia Max", round(float(max_fm), 2))

        if "Quotazione" in df_filtrato.columns:
            quot_med = (
                df_filtrato["Quotazione"].mean() if not df_filtrato.empty else 0
            )
            col3.metric("Quotazione Media", round(float(quot_med), 1))

        if "FVM" in df_filtrato.columns:
            fvm_max = df_filtrato["FVM"].max() if not df_filtrato.empty else 0
            col4.metric("FVM Max", int(fvm_max))

        st.write("---")

        colonne_prioritarie = [
            "Calciatore",
            "Squadra",
            "Ruolo",
            "Status",
            "Quotazione",
            "FantaMedia",
            "MediaVoto",
            "PartiteVoto",
            "FVM",
            "FantaSquadra",
            "Costo",
        ]
        colonne_presenti = [
            c for c in colonne_prioritarie if c in df_filtrato.columns
        ]
        altre_colonne = [
            c for c in df_filtrato.columns if c not in colonne_presenti
        ]
        st.dataframe(
            df_filtrato[colonne_presenti + altre_colonne],
            use_container_width=True,
            hide_index=True,
        )

    # ---------------------------------------------------------
    # TAB 2: GRAFICO OCCASIONI
    # ---------------------------------------------------------
    with tab2:
        st.subheader("🎯 Mappa delle Occasioni: FantaMedia vs Quotazione")
        st.markdown(
            "I giocatori **in alto a sinistra** (alta FantaMedia, bassa Quotazione)"
            " rappresentano i **migliori affari**."
        )

        df_chart = df_filtrato.copy()
        if "PartiteVoto" in df_chart.columns:
            df_chart = df_chart[df_chart["PartiteVoto"] > 0]

        if not df_chart.empty and {"Quotazione", "FantaMedia"}.issubset(
            df_chart.columns
        ):
            fig = px.scatter(
                df_chart,
                x="Quotazione",
                y="FantaMedia",
                color="Ruolo" if "Ruolo" in df_chart.columns else None,
                hover_name="Calciatore",
                hover_data=[
                    c
                    for c in [
                        "Squadra",
                        "Status",
                        "MediaVoto",
                        "PartiteVoto",
                        "FantaSquadra",
                        "Costo",
                    ]
                    if c in df_chart.columns
                ],
                size="PartiteVoto" if "PartiteVoto" in df_chart.columns else None,
                size_max=15,
                title="FantaMedia in rapporto al Prezzo / Quotazione",
                labels={
                    "Quotazione": "Quotazione Attuale",
                    "FantaMedia": "FantaMedia (FM)",
                },
            )
            fig.add_hline(
                y=df_chart["FantaMedia"].median(),
                line_dash="dot",
                line_color="gray",
                annotation_text="FM Mediana",
            )
            fig.add_vline(
                x=df_chart["Quotazione"].median(),
                line_dash="dot",
                line_color="gray",
                annotation_text="Quotazione Mediana",
            )
            fig.update_layout(height=600)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato disponibile con i filtri correnti.")

    # ---------------------------------------------------------
    # TAB 3: ANALISI ROSE LEGA
    # ---------------------------------------------------------
    with tab3:
        st.subheader("🛡️ Analisi Dettagliata Rosa FantaSquadra")

        if lista_squadre:
            squadra_scelta = st.selectbox(
                "Seleziona la FantaSquadra da analizzare:",
                lista_squadre,
                key="tab3_sq",
            )
            df_squadra = df[df["FantaSquadra"].astype(str) == squadra_scelta].copy()

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Giocatori in Rosa", len(df_squadra))

            tot_speso = (
                df_squadra["Costo"].sum() if "Costo" in df_squadra.columns else 0
            )
            kpi2.metric("Crediti Spesi Totali", f"{int(tot_speso)}")

            fm_media_squadra = (
                df_squadra[df_squadra["PartiteVoto"] > 0]["FantaMedia"].mean()
                if "FantaMedia" in df_squadra.columns
                else 0
            )
            kpi3.metric(
                "FantaMedia Media Rosa",
                round(float(fm_media_squadra), 2)
                if pd.notna(fm_media_squadra)
                else 0,
            )

            top_player = (
                df_squadra.sort_values(by="FantaMedia", ascending=False).iloc[0][
                    "Calciatore"
                ]
                if not df_squadra.empty and "FantaMedia" in df_squadra.columns
                else "-"
            )
            kpi4.metric("Top Player (FM)", top_player)

            st.write("---")

            c_graf1, c_graf2 = st.columns(2)

            with c_graf1:
                st.markdown("**Composizione Rosa per Ruolo**")
                conteggio_ruolo = (
                    df_squadra["Ruolo"].value_counts().reset_index()
                    if "Ruolo" in df_squadra.columns
                    else pd.DataFrame()
                )
                if not conteggio_ruolo.empty:
                    conteggio_ruolo.columns = ["Ruolo", "Conteggio"]
                    fig_bar = px.bar(
                        conteggio_ruolo,
                        x="Ruolo",
                        y="Conteggio",
                        color="Ruolo",
                        text="Conteggio",
                        title="Numero Giocatori per Reparto",
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            with c_graf2:
                st.markdown("**Distribuzione Spesa Crediti**")
                if "Costo" in df_squadra.columns and "Ruolo" in df_squadra.columns:
                    spesa_ruolo = (
                        df_squadra.groupby("Ruolo")["Costo"].sum().reset_index()
                    )
                    fig_pie = px.pie(
                        spesa_ruolo,
                        values="Costo",
                        names="Ruolo",
                        title="Crediti Spesi per Reparto",
                        color="Ruolo",
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            st.write("---")
            st.markdown(f"**Rosa Completa: {squadra_scelta}**")

            cols_display = [
                c
                for c in [
                    "Calciatore",
                    "Ruolo",
                    "Squadra",
                    "Status",
                    "Costo",
                    "FantaMedia",
                    "MediaVoto",
                    "PartiteVoto",
                    "Quotazione",
                ]
                if c in df_squadra.columns
            ]
            st.dataframe(
                df_squadra[cols_display].sort_values(by="Ruolo", ascending=True),
                use_container_width=True,
                hide_index=True,
            )

    # ---------------------------------------------------------
    # TAB 4: VALUTATORE DI SCAMBI
    # ---------------------------------------------------------
    with tab4:
        st.subheader("🔄 Valutatore Scambi (Trade Analyzer)")

        t_col1, t_col2 = st.columns(2)

        with t_col1:
            st.markdown("### 🅰️ Giocatori che CEDO")
            squadra_A = st.selectbox(
                "Seleziona la tua FantaSquadra:", lista_squadre, key="sq_A"
            )
            df_squadra_A = df[df["FantaSquadra"].astype(str) == squadra_A]
            giocatori_ceduti = st.multiselect(
                "Seleziona i giocatori che vuoi scambiare:",
                options=df_squadra_A["Calciatore"].tolist(),
                key="ceduti",
            )

        with t_col2:
            st.markdown("### 🅱️ Giocatori che RICEVO")
            squadre_B_opts = [s for s in lista_squadre if s != squadra_A]
            squadra_B = st.selectbox(
                "Seleziona la FantaSquadra avversaria:", squadre_B_opts, key="sq_B"
            )
            df_squadra_B = df[df["FantaSquadra"].astype(str) == squadra_B]
            giocatori_ricevuti = st.multiselect(
                "Seleziona i giocatori che vuoi ricevere:",
                options=df_squadra_B["Calciatore"].tolist(),
                key="ricevuti",
            )

        st.write("---")

        if giocatori_ceduti and giocatori_ricevuti:
            df_ceduti = df_squadra_A[
                df_squadra_A["Calciatore"].isin(giocatori_ceduti)
            ]
            df_ricevuti = df_squadra_B[
                df_squadra_B["Calciatore"].isin(giocatori_ricevuti)
            ]

            fm_ceduta = (
                df_ceduti["FantaMedia"].sum() if "FantaMedia" in df_ceduti else 0
            )
            fm_ricevuta = (
                df_ricevuti["FantaMedia"].sum() if "FantaMedia" in df_ricevuti else 0
            )
            diff_fm = fm_ricevuta - fm_ceduta

            quot_ceduta = (
                df_ceduti["Quotazione"].sum() if "Quotazione" in df_ceduti else 0
            )
            quot_ricevuta = (
                df_ricevuti["Quotazione"].sum() if "Quotazione" in df_ricevuti else 0
            )
            diff_quot = quot_ricevuta - quot_ceduta

            fvm_ceduto = df_ceduti["FVM"].sum() if "FVM" in df_ceduti else 0
            fvm_ricevuto = df_ricevuti["FVM"].sum() if "FVM" in df_ricevuto else 0
            diff_fvm = fvm_ricevuto - fvm_ceduto

            st.markdown("### ⚖️ Bilancio dello Scambio")

            res_col1, res_col2, res_col3 = st.columns(3)
            res_col1.metric("Delta FantaMedia Totale", f"{diff_fm:+.2f}")
            res_col2.metric("Delta Quotazione Totale", f"{diff_quot:+.0f}")
            res_col3.metric("Delta FVM (FantaValorMedio)", f"{diff_fvm:+.0f}")

            if diff_fm > 0 and diff_fvm >= 0:
                st.success(
                    "🟢 **Scambio Vantaggioso:** Guadagno in FantaMedia e valore"
                    " complessivo!"
                )
            elif diff_fm < 0 and diff_fvm < 0:
                st.error(
                    "🔴 **Scambio Svantaggioso:** Perdi sia FantaMedia che valore di"
                    " rosa."
                )
            else:
                st.warning(
                    "🟡 **Scambio Equilibrato / Strategico:** Stai ridistribuendo i"
                    " ruoli tra i reparti."
                )

            c_det1, c_det2 = st.columns(2)
            cols_show = [
                c
                for c in [
                    "Calciatore",
                    "Ruolo",
                    "Squadra",
                    "Status",
                    "FantaMedia",
                    "Quotazione",
                    "FVM",
                ]
                if c in df.columns
            ]

            with c_det1:
                st.markdown("**Giocatori Ceduti**")
                st.dataframe(
                    df_ceduti[cols_show], hide_index=True, use_container_width=True
                )

            with c_det2:
                st.markdown("**Giocatori Ricevuti**")
                st.dataframe(
                    df_ricevuti[cols_show], hide_index=True, use_container_width=True
                )

    # ---------------------------------------------------------
    # TAB 5: REPORT & OTTIMIZZATORE MODULO
    # ---------------------------------------------------------
    with tab5:
        st.subheader("📄 Report & Ottimizzatore Modulo (con Modificatore Difesa)")

        if lista_squadre:
            rep_col1, rep_col2 = st.columns([2, 1])

            with rep_col1:
                squadra_rep = st.selectbox(
                    "Seleziona FantaSquadra:", lista_squadre, key="rep_sq"
                )

            with rep_col2:
                usa_modificatore = st.checkbox(
                    "Attiva Modificatore Difesa", value=True
                )

            df_squadra_rep = df[
                df["FantaSquadra"].astype(str) == squadra_rep
            ].copy()

            if not df_squadra_rep.empty:
                df_squadra_rep["FantaMedia_clean"] = pd.to_numeric(
                    df_squadra_rep["FantaMedia"], errors="coerce"
                ).fillna(0)
                df_squadra_rep["MediaVoto_clean"] = pd.to_numeric(
                    df_squadra_rep["MediaVoto"], errors="coerce"
                ).fillna(0)

                moduli = [
                    (3, 4, 3),
                    (3, 5, 2),
                    (4, 3, 3),
                    (4, 4, 2),
                    (4, 5, 1),
                    (5, 3, 2),
                    (5, 4, 1),
                ]
                risultati_moduli = []

                for d_c, c_c, a_c in moduli:
                    p = df_squadra_rep[df_squadra_rep["Ruolo"] == "P"].nlargest(
                        1, "FantaMedia_clean"
                    )
                    d = df_squadra_rep[df_squadra_rep["Ruolo"] == "D"].nlargest(
                        d_c, "FantaMedia_clean"
                    )
                    c = df_squadra_rep[df_squadra_rep["Ruolo"] == "C"].nlargest(
                        c_c, "FantaMedia_clean"
                    )
                    a = df_squadra_rep[df_squadra_rep["Ruolo"] == "A"].nlargest(
                        a_c, "FantaMedia_clean"
                    )

                    if (
                        len(p) < 1
                        or len(d) < d_c
                        or len(c) < c_c
                        or len(a) < a_c
                    ):
                        continue

                    lineup = pd.concat([p, d, c, a])
                    base_fm = lineup["FantaMedia_clean"].sum()

                    mod_bonus = 0
                    if usa_modificatore and d_c >= 4:
                        gk_mv = p["MediaVoto_clean"].iloc[0]
                        defs_mv = sorted(d["MediaVoto_clean"].tolist(), reverse=True)[:3]
                        if len(defs_mv) == 3:
                            avg_def = (gk_mv + sum(defs_mv)) / 4.0
                            if avg_def >= 7.0:
                                mod_bonus = 6
                            elif avg_def >= 6.75:
                                mod_bonus = 5
                            elif avg_def >= 6.5:
                                mod_bonus = 4
                            elif avg_def >= 6.25:
                                mod_bonus = 3
                            elif avg_def >= 6.0:
                                mod_bonus = 1

                    tot_score = base_fm + mod_bonus
                    risultati_moduli.append({
                        "Modulo": f"{d_c}-{c_c}-{a_c}",
                        "Base FM": round(base_fm, 2),
                        "Bonus Modificatore": mod_bonus,
                        "Punteggio Totale Atteso": round(tot_score, 2),
                        "Lineup": lineup,
                    })

                df_moduli = pd.DataFrame(risultati_moduli).sort_values(
                    by="Punteggio Totale Atteso", ascending=False
                )

                if not df_moduli.empty:
                    miglior_modulo = df_moduli.iloc[0]

                    st.write("---")
                    kpi_m1, kpi_m2, kpi_m3, kpi_m4 = st.columns(4)
                    kpi_m1.metric("Modulo Consigliato", miglior_modulo["Modulo"])
                    kpi_m2.metric(
                        "Punteggio Totale Atteso",
                        f"{miglior_modulo['Punteggio Totale Atteso']:.2f}",
                    )
                    kpi_m3.metric(
                        "Somma FantaMedia Base", f"{miglior_modulo['Base FM']:.2f}"
                    )
                    kpi_m4.metric(
                        "Bonus Modificatore", f"+{miglior_modulo['Bonus Modificatore']}"
                    )

                    st.write("---")
                    st.markdown("### 📊 Confronto Rendimento Moduli Tattici")
                    st.dataframe(
                        df_moduli[
                            ["Modulo", "Base FM", "Bonus Modificatore", "Punteggio Totale Atteso"]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                    top_11 = miglior_modulo["Lineup"]
                    st.markdown(
                        f"### 🏟️ XI Titolare Consigliato ({miglior_modulo['Modulo']}) -"
                        f" {squadra_rep}"
                    )

                    cols_rep = [
                        c
                        for c in [
                            "Ruolo",
                            "Calciatore",
                            "Squadra",
                            "Status",
                            "FantaMedia",
                            "MediaVoto",
                            "PartiteVoto",
                            "Costo",
                        ]
                        if c in top_11.columns
                    ]
                    st.dataframe(
                        top_11[cols_rep],
                        use_container_width=True,
                        hide_index=True,
                    )

    # ---------------------------------------------------------
    # TAB 6: SIMULATORE SCONTRI DIRETTI
    # ---------------------------------------------------------
    with tab_sim:
        st.subheader("⚔️ Simulatore Scontri Diretti")
        st.markdown(
            "Simula una sfida diretta tra due FantaSquadre calcolando i punti attesi e i gol segnati in base al miglior XI schierabile."
        )

        if len(lista_squadre) >= 2:
            col_sim1, col_sim2 = st.columns(2)

            with col_sim1:
                sq_casa = st.selectbox(
                    "FantaSquadra Casa:",
                    lista_squadre,
                    key="sim_sq_casa",
                )
            with col_sim2:
                opts_trasferta = [s for s in lista_squadre if s != sq_casa]
                sq_trasferta = st.selectbox(
                    "FantaSquadra Trasferta:",
                    opts_trasferta,
                    key="sim_sq_trasferta",
                )

            col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
            mod_casa = col_cfg1.selectbox(
                "Modulo Casa:",
                [(3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 3, 2), (5, 4, 1)],
                index=2,
                key="mod_casa",
            )
            mod_trasferta = col_cfg2.selectbox(
                "Modulo Trasferta:",
                [(3, 4, 3), (3, 5, 2), (4, 3, 3), (4, 4, 2), (4, 5, 1), (5, 3, 2), (5, 4, 1)],
                index=2,
                key="mod_trasferta",
            )
            soglia_gol = col_cfg3.number_input(
                "Soglia Primo Gol:", value=66.0, step=0.5
            )

            if st.button("🚀 Simula Partita", use_container_width=True):
                df_casa = df[df["FantaSquadra"].astype(str) == sq_casa]
                df_trasferta = df[df["FantaSquadra"].astype(str) == sq_trasferta]

                xi_casa = calcola_miglior_xi(df_casa, modulo=mod_casa)
                xi_trasferta = calcola_miglior_xi(df_trasferta, modulo=mod_trasferta)

                if xi_casa is None or xi_trasferta is None:
                    st.error(
                        "Una o entrambe le squadre non hanno abbastanza giocatori titolari disponibili per il modulo selezionato."
                    )
                else:
                    punti_casa = xi_casa["FM_clean"].sum()
                    punti_trasferta = xi_trasferta["FM_clean"].sum()

                    gol_casa = calcola_gol(punti_casa, soglia_primo_gol=soglia_gol)
                    gol_trasferta = calcola_gol(punti_trasferta, soglia_primo_gol=soglia_gol)

                    st.write("---")
                    st.markdown("### 🏟️ Risultato Finale")

                    res_col1, res_col2, res_col3 = st.columns([2, 1, 2])
                    with res_col1:
                        st.metric(
                            label=f"🏠 {sq_casa}",
                            value=f"{gol_casa} Gol",
                            delta=f"{punti_casa:.2f} Punti Totali",
                        )
                    with res_col2:
                        st.markdown(
                            f"<h1 style='text-align: center; margin: 0;'>{gol_casa} - {gol_trasferta}</h1>",
                            unsafe_allow_html=True,
                        )
                    with res_col3:
                        st.metric(
                            label=f"✈️ {sq_trasferta}",
                            value=f"{gol_trasferta} Gol",
                            delta=f"{punti_trasferta:.2f} Punti Totali",
                        )

                    if gol_casa > gol_trasferta:
                        st.success(f"🎉 **Vittoria per {sq_casa}!**")
                    elif gol_trasferta > gol_casa:
                        st.success(f"🎉 **Vittoria per {sq_trasferta}!**")
                    else:
                        st.info("🤝 **Pareggio!**")

                    c_lineup1, c_lineup2 = st.columns(2)
                    cols_view = [c for c in ["Ruolo", "Calciatore", "Squadra", "FantaMedia"] if c in xi_casa.columns]

                    with c_lineup1:
                        st.markdown(f"**XI Titolare {sq_casa} ({mod_casa[0]}-{mod_casa[1]}-{mod_casa[2]})**")
                        st.dataframe(xi_casa[cols_view], hide_index=True, use_container_width=True)

                    with c_lineup2:
                        st.markdown(f"**XI Titolare {sq_trasferta} ({mod_trasferta[0]}-{mod_trasferta[1]}-{mod_trasferta[2]})**")
                        st.dataframe(xi_trasferta[cols_view], hide_index=True, use_container_width=True)
        else:
            st.info("Sono necessarie almeno 2 FantaSquadre per simulare uno scontro diretto.")
else:
    st.info("👈 Carica un file Excel o CSV dalla barra laterale per iniziare.")
