import io
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Fanta Analyzer & Asta Live", page_icon="⚽", layout="wide"
)


# Funzione per pulire e normalizzare i ruoli in P, D, C, A
def normalizza_ruolo(r):
    if pd.isna(r) or r is None:
        return ""
    s = str(r).strip().upper()
    if s in ["P", "POR", "PORTIERE", "POR (P)"] or s.startswith("P"):
        return "P"
    if s in ["D", "DIF", "DIFENSORE", "DIF (D)"] or s.startswith("D"):
        return "D"
    if s in ["C", "CEN", "CENTROCAMPISTA", "CEN (C)"] or s.startswith("C"):
        return "C"
    if s in ["A", "ATT", "ATTACCANTE", "ATT (A)"] or s.startswith("A"):
        return "A"
    return s


# Funzione di riavvio compatibile con tutte le versioni di Streamlit
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


# ---------------------------------------------------------
# INIZIALIZZAZIONE SESSION STATE
# ---------------------------------------------------------
if "asta_history" not in st.session_state:
    st.session_state["asta_history"] = []

if "df_data" not in st.session_state:
    st.session_state["df_data"] = None

st.title("⚽ Fanta Analyzer - Dashboard, Asta Live & Simulatore")

# ---------------------------------------------------------
# 1. SIDEBAR: CARICAMENTO FILE
# ---------------------------------------------------------
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
                else (
                    "Lista calciatori"
                    if "Lista calciatori" in xls.sheet_names
                    else xls.sheet_names[0]
                )
            )
            df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)

        # Conversione e pulizia nomi colonne
        df_raw.columns = df_raw.columns.astype(str).str.strip()

        # Rilevamento automatico riga intestazione
        if not any(
            col in df_raw.columns
            for col in ["Calciatore", "Nome", "R", "Ruolo"]
        ):
            for idx_row, row in df_raw.iloc[:5].iterrows():
                row_str = row.astype(str).values
                if any(
                    "Nome" in val
                    or "Calciatore" in val
                    or "Ruolo" in val
                    or "R" in val
                    for val in row_str
                ):
                    df_raw.columns = df_raw.iloc[idx_row].astype(str).str.strip()
                    df_raw = df_raw.iloc[idx_row + 1 :].reset_index(drop=True)
                    break

        # Mappatura colonne standard Fantacalcio
        mappatura = {
            "R": "Ruolo",
            "RM": "Ruolo Mantra",
            "Ruolo Classic": "Ruolo",
            "Posizione": "Ruolo",
            "Nome": "Calciatore",
            "Giocatore": "Calciatore",
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
            "FantaSquadra": "FantaSquadra",
            "Squadra Fantacalcio": "FantaSquadra",
        }
        df_raw = df_raw.rename(columns=mappatura)

        # Garanzia colonna Calciatore
        if "Calciatore" not in df_raw.columns:
            for col in df_raw.columns:
                if df_raw[col].dtype == "object":
                    df_raw = df_raw.rename(columns={col: "Calciatore"})
                    break
            if "Calciatore" not in df_raw.columns:
                df_raw["Calciatore"] = [
                    f"Giocatore {i+1}" for i in range(len(df_raw))
                ]

        # Garanzia e normalizzazione colonna Ruolo
        if "Ruolo" not in df_raw.columns:
            df_raw["Ruolo"] = "A"
        else:
            df_raw["Ruolo"] = df_raw["Ruolo"].apply(normalizza_ruolo)

        # Garanzia colonna Status
        if "Status" not in df_raw.columns:
            df_raw["Status"] = "Disponibile"
        else:
            df_raw["Status"] = (
                df_raw["Status"].fillna("Disponibile").astype(str)
            )
            df_raw["Status"] = df_raw["Status"].replace(
                ["", "-", "nan", "None"], "Disponibile"
            )

        # Garanzia colonna FantaSquadra
        if "FantaSquadra" not in df_raw.columns:
            df_raw["FantaSquadra"] = None
        else:
            df_raw["FantaSquadra"] = (
                df_raw["FantaSquadra"].astype(str).str.strip()
            )
            df_raw["FantaSquadra"] = df_raw["FantaSquadra"].replace(
                ["nan", "None", "", "NaN"], None
            )

        if "Costo" not in df_raw.columns:
            df_raw["Costo"] = 0

        # Pulizia numeri
        num_cols = [
            "Quotazione",
            "FantaMedia",
            "MediaVoto",
            "PartiteVoto",
            "FVM",
            "Costo",
        ]
        for nc in num_cols:
            if nc in df_raw.columns:
                df_raw[nc] = (
                    df_raw[nc]
                    .astype(str)
                    .str.replace(",", ".")
                    .replace(["nan", "None", ""], "0")
                )
                df_raw[nc] = pd.to_numeric(df_raw[nc], errors="coerce").fillna(0)
            else:
                df_raw[nc] = 0

        st.session_state["df_data"] = df_raw
        st.sidebar.success(f"File caricato! ({len(df_raw)} calciatori)")
    except Exception as e:
        st.sidebar.error(f"Errore nel caricamento del file: {e}")

# Pulsante Reset File
if st.session_state["df_data"] is not None:
    if st.sidebar.button("🗑️ Rimuovi/Ricarica File"):
        st.session_state["df_data"] = None
        st.session_state["asta_history"] = []
        safe_rerun()

df = st.session_state["df_data"]


# ---------------------------------------------------------
# FUNZIONI DI CALCOLO FORMAZIONE E GOL
# ---------------------------------------------------------
def calcola_miglior_xi(df_squadra, modulo=(3, 4, 3)):
    if df_squadra is None or df_squadra.empty:
        return None, "Nessun giocatore in rosa."

    df_temp = df_squadra.copy()
    df_temp.columns = df_temp.columns.astype(str).str.strip()

    # Individuazione automatica colonna del ruolo
    col_ruolo = None
    for col in ["Ruolo", "R", "Ruolo Classic", "RM", "Posizione"]:
        if col in df_temp.columns:
            col_ruolo = col
            break

    if col_ruolo is None:
        return None, (
            f"Colonna Ruolo non trovata. Colonne presenti: {list(df_temp.columns)}"
        )

    df_temp["Ruolo_Clean"] = df_temp[col_ruolo].apply(normalizza_ruolo)

    # Individuazione colonna media voto / fantamedia
    fm_col = "FantaMedia"
    if "FantaMedia" not in df_temp.columns:
        if "FM" in df_temp.columns:
            fm_col = "FM"
        elif "Quotazione" in df_temp.columns:
            fm_col = "Quotazione"
        else:
            df_temp["FM_clean"] = 6.0
            fm_col = "FM_clean"

    if fm_col != "FM_clean":
        df_temp["FM_clean"] = (
            pd.to_numeric(df_temp[fm_col], errors="coerce").fillna(6.0)
        )

    d_c, c_c, a_c = modulo

    p = df_temp[df_temp["Ruolo_Clean"] == "P"].nlargest(1, "FM_clean")
    d = df_temp[df_temp["Ruolo_Clean"] == "D"].nlargest(d_c, "FM_clean")
    c = df_temp[df_temp["Ruolo_Clean"] == "C"].nlargest(c_c, "FM_clean")
    a = df_temp[df_temp["Ruolo_Clean"] == "A"].nlargest(a_c, "FM_clean")

    mancanti = []
    if len(p) < 1:
        mancanti.append(f"Portieri ({len(p)}/1)")
    if len(d) < d_c:
        mancanti.append(f"Difensori ({len(d)}/{d_c})")
    if len(c) < c_c:
        mancanti.append(f"Centrocampisti ({len(c)}/{c_c})")
    if len(a) < a_c:
        mancanti.append(f"Attaccanti ({len(a)}/{a_c})")

    if mancanti:
        return None, (
            f"Mancano sufficienti giocatori per il modulo"
            f" {d_c}-{c_c}-{a_c}: {', '.join(mancanti)}"
        )

    return pd.concat([p, d, c, a]), None


def calcola_gol(punti, soglia_primo_gol=66.0, passo_gol=6.0):
    if punti < soglia_primo_gol:
        return 0
    return int((punti - soglia_primo_gol) // passo_gol) + 1


# ---------------------------------------------------------
# INTERFACCIA UTENTE PRINCIPALE
# ---------------------------------------------------------
if df is None:
    st.info(
        "👈 **Per iniziare, carica un file Excel (.xlsx) o CSV dal menu"
        " laterale a sinistra.**"
    )
else:
    # Sidebar impostazioni
    st.sidebar.write("---")
    st.sidebar.header("⚙️ 2. Impostazioni Asta Live")

    budget_iniziale = st.sidebar.number_input(
        "Budget Iniziale (Crediti)", min_value=100, max_value=2000, value=500
    )

    col_s1, col_s2 = st.sidebar.columns(2)
    target_P = col_s1.number_input("Slot P", value=3, min_value=1)
    target_D = col_s2.number_input("Slot D", value=8, min_value=1)
    target_C = col_s1.number_input("Slot C", value=8, min_value=1)
    target_A = col_s2.number_input("Slot A", value=6, min_value=1)
    target_slots = {"P": target_P, "D": target_D, "C": target_C, "A": target_A}
    tot_slots_target = sum(target_slots.values())

    fantasquadre_esistenti = sorted([
        str(x).strip()
        for x in df["FantaSquadra"].dropna().unique()
        if str(x).strip() != "" and str(x) != "None"
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

    if "Status" in df_filtrato.columns:
        escludi_indisponibili = st.sidebar.checkbox(
            "Escludi Infortunati e Squalificati", value=False
        )
        if escludi_indisponibili:
            parole_chiave = ["inf", "squalific", "fuori", "cedut"]
            pattern = "|".join(parole_chiave)
            df_filtrato = df_filtrato[
                ~df_filtrato["Status"]
                .astype(str)
                .str.lower()
                .str.contains(pattern, regex=True)
            ]

    stato_opzioni = ["Tutti", "Solo Svincolati", "Solo Acquistati"]
    stato_sel = st.sidebar.selectbox("Stato Calciatore", stato_opzioni)

    if stato_sel == "Solo Svincolati":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].isna()
            | (df_filtrato["FantaSquadra"] == "")
            | (df_filtrato["FantaSquadra"] == "None")
        ]
    elif stato_sel == "Solo Acquistati":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].notna()
            & (df_filtrato["FantaSquadra"] != "")
            & (df_filtrato["FantaSquadra"] != "None")
        ]

    fantasquadre_filtro = ["Tutte"] + lista_squadre
    fantasquadra_sel = st.sidebar.selectbox(
        "FantaSquadra da Filtrare", fantasquadre_filtro
    )
    if fantasquadra_sel != "Tutte":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].astype(str).str.strip()
            == fantasquadra_sel.strip()
        ]

    if "Ruolo" in df.columns:
        ruoli = ["Tutti"] + list(df["Ruolo"].dropna().astype(str).unique())
        ruolo_sel = st.sidebar.selectbox("Ruolo Classic", ruoli)
        if ruolo_sel != "Tutti":
            df_filtrato = df_filtrato[
                df_filtrato["Ruolo"].astype(str) == ruolo_sel
            ]

    if "Calciatore" in df.columns:
        nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")
        if nome_cercato:
            df_filtrato = df_filtrato[
                df_filtrato["Calciatore"]
                .astype(str)
                .str.contains(nome_cercato, case=False)
            ]

    # TAB RAGGRUPPATI
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
    # TAB: ASTA LIVE
    # ---------------------------------------------------------
    with tab_asta:
        st.subheader("⚡ Chiamata & Chiusura Asta in Tempo Reale")
        col_chiamata, col_target = st.columns([1.2, 1])

        svincolati_df = df[
            df["FantaSquadra"].isna()
            | (df["FantaSquadra"] == "")
            | (df["FantaSquadra"] == "None")
        ].sort_values(
            by="FVM" if "FVM" in df.columns else "Calciatore", ascending=False
        )
        opzioni_giocatori = svincolati_df["Calciatore"].tolist()

        with col_chiamata:
            st.markdown("### 🏷️ Registra Acquisto")

            if opzioni_giocatori:
                giocatore_chiamato = st.selectbox(
                    "Seleziona Calciatore:", opzioni_giocatori
                )
                sq_acquirente = st.selectbox("Acquistato da:", lista_squadre)
                prezzo_acquisto = st.number_input(
                    "Prezzo di Aggiudicazione (Crediti):",
                    min_value=1,
                    max_value=budget_iniziale,
                    value=1,
                )

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button(
                        "✅ Registra Acquisto", use_container_width=True
                    ):
                        idx = df[df["Calciatore"] == giocatore_chiamato].index[
                            0
                        ]
                        st.session_state["df_data"].loc[
                            idx, "FantaSquadra"
                        ] = sq_acquirente
                        st.session_state["df_data"].loc[idx, "Costo"] = (
                            prezzo_acquisto
                        )
                        st.session_state["asta_history"].append((
                            giocatore_chiamato,
                            sq_acquirente,
                            prezzo_acquisto,
                        ))
                        st.success(
                            f"Aggiudicato **{giocatore_chiamato}** a"
                            f" **{sq_acquirente}** per **{prezzo_acquisto}"
                            " cr**!"
                        )
                        safe_rerun()

                with c_btn2:
                    if (
                        st.button(
                            "↩️ Annulla Ultimo Acquisto",
                            use_container_width=True,
                        )
                        and st.session_state["asta_history"]
                    ):
                        g_last, sq_last, p_last = st.session_state[
                            "asta_history"
                        ].pop()
                        idx = df[df["Calciatore"] == g_last].index[0]
                        st.session_state["df_data"].loc[idx, "FantaSquadra"] = (
                            None
                        )
                        st.session_state["df_data"].loc[idx, "Costo"] = 0
                        st.warning(f"Annullato acquisto di {g_last}.")
                        safe_rerun()
            else:
                st.info("Tutti i calciatori sono stati acquistati!")

        with col_target:
            st.markdown("### 🎯 Moneyball Target: Prezzo Max Consigliato")
            if opzioni_giocatori:
                info_g = df[df["Calciatore"] == giocatore_chiamato].iloc[0]
                ruolo_g = str(info_g.get("Ruolo", "A"))
                status_txt = str(info_g.get("Status", "Disponibile"))
                fvm_g = float(info_g.get("FVM", 0))
                fm_g = float(info_g.get("FantaMedia", 0))

                df_sq_acq = df[
                    df["FantaSquadra"].astype(str).str.strip()
                    == sq_acquirente.strip()
                ]
                spesi_acq = df_sq_acq["Costo"].sum()
                rimasti_acq = budget_iniziale - spesi_acq

                presi_ruolo = (
                    len(df_sq_acq[df_sq_acq["Ruolo"] == ruolo_g])
                    if "Ruolo" in df_sq_acq.columns
                    else 0
                )
                slot_rimasti_ruolo = max(
                    1, target_slots.get(ruolo_g, 6) - presi_ruolo
                )
                tot_slot_rimasti = max(1, tot_slots_target - len(df_sq_acq))

                fvm_scale = 1000.0 if fvm_g > 0 else 1.0
                budget_target_ruolo = (
                    rimasti_acq * (fvm_g / fvm_scale) * 1.6
                )
                max_bid_possibile = rimasti_acq - (tot_slot_rimasti - 1)
                prezzo_max_consigliato = max(
                    1, min(int(round(budget_target_ruolo)), max_bid_possibile)
                )

                st.metric(
                    label=f"Prezzo Max Consigliato per {info_g['Calciatore']}",
                    value=f"{prezzo_max_consigliato} cr",
                    delta=f"Slot {ruolo_g} Rimanenti: {slot_rimasti_ruolo}",
                )

                st.write(
                    f"**Ruolo:** `{ruolo_g}` | **Squadra:**"
                    f" `{info_g.get('Squadra', '-')}`"
                )
                st.write(f"**Condizione:** {status_txt}")
                st.write(
                    f"**FVM:** `{int(fvm_g)}` | **FantaMedia:** `{fm_g:.2f}`"
                )
                st.write(
                    f"**Crediti Residui ({sq_acquirente}):** `{rimasti_acq} cr`"
                )

        st.write("---")

        # Tabella Monitor Crediti
        st.markdown("### 📊 Monitor Crediti e Slot Rose Lega")
        report_rose = []
        for sq in lista_squadre:
            df_sq = df[
                df["FantaSquadra"].astype(str).str.strip() == sq.strip()
            ].copy()
            spesi = df_sq["Costo"].sum() if "Costo" in df_sq.columns else 0
            residui = budget_iniziale - spesi

            if "Ruolo" in df_sq.columns:
                p_count = len(df_sq[df_sq["Ruolo"] == "P"])
                d_count = len(df_sq[df_sq["Ruolo"] == "D"])
                c_count = len(df_sq[df_sq["Ruolo"] == "C"])
                a_count = len(df_sq[df_sq["Ruolo"] == "A"])
            else:
                p_count = d_count = c_count = a_count = 0

            tot_in_rosa = len(df_sq)
            slot_rimasti_tot = max(0, tot_slots_target - tot_in_rosa)
            max_bid = (
                residui - (slot_rimasti_tot - 1) if slot_rimasti_tot > 0 else 0
            )

            report_rose.append({
                "FantaSquadra": sq,
                "Crediti Spesi": int(spesi),
                "Crediti Residui": int(residui),
                "Max Offerta": max(0, int(max_bid)),
                "P": f"{p_count}/{target_P}",
                "D": f"{d_count}/{target_D}",
                "C": f"{c_count}/{target_C}",
                "A": f"{a_count}/{target_A}",
                "Totale Rosa": f"{tot_in_rosa}/{tot_slots_target}",
            })

        st.dataframe(
            pd.DataFrame(report_rose), use_container_width=True, hide_index=True
        )

    # ---------------------------------------------------------
    # TAB 1: LISTA GENERALE
    # ---------------------------------------------------------
    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Calciatori Selezionati", len(df_filtrato))
        col2.metric(
            "FantaMedia Max",
            round(
                float(
                    df_filtrato["FantaMedia"].max()
                    if not df_filtrato.empty
                    else 0
                ),
                2,
            ),
        )
        col3.metric(
            "Quotazione Media",
            round(
                float(
                    df_filtrato["Quotazione"].mean()
                    if not df_filtrato.empty
                    else 0
                ),
                1,
            ),
        )
        col4.metric(
            "FVM Max",
            int(df_filtrato["FVM"].max() if not df_filtrato.empty else 0),
        )

        st.write("---")
        cols_prioritarie = [
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
        cols_presenti = [
            c for c in cols_prioritarie if c in df_filtrato.columns
        ]
        cols_altre = [c for c in df_filtrato.columns if c not in cols_presenti]
        st.dataframe(
            df_filtrato[cols_presenti + cols_altre],
            use_container_width=True,
            hide_index=True,
        )

    # ---------------------------------------------------------
    # TAB 2: GRAFICO OCCASIONI
    # ---------------------------------------------------------
    with tab2:
        st.subheader("🎯 Mappa delle Occasioni: FantaMedia vs Quotazione")
        df_chart = (
            df_filtrato[df_filtrato["PartiteVoto"] > 0]
            if "PartiteVoto" in df_filtrato.columns
            else df_filtrato.copy()
        )

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
                title="FantaMedia in rapporto al Prezzo / Quotazione",
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
                "Seleziona FantaSquadra:", lista_squadre, key="tab3_sq"
            )
            df_squadra = df[
                df["FantaSquadra"].astype(str).str.strip()
                == squadra_scelta.strip()
            ].copy()

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Giocatori in Rosa", len(df_squadra))
            kpi2.metric("Crediti Spesi Totali", int(df_squadra["Costo"].sum()))
            kpi3.metric(
                "FantaMedia Media Rosa",
                round(
                    float(
                        df_squadra["FantaMedia"].mean()
                        if not df_squadra.empty
                        else 0
                    ),
                    2,
                ),
            )

            st.write("---")
            cols_disp = [
                c
                for c in [
                    "Calciatore",
                    "Ruolo",
                    "Squadra",
                    "Status",
                    "Costo",
                    "FantaMedia",
                    "Quotazione",
                ]
                if c in df_squadra.columns
            ]
            st.dataframe(
                df_squadra[cols_disp],
                use_container_width=True,
                hide_index=True,
            )

    # ---------------------------------------------------------
    # TAB 4: VALUTATORE SCAMBI
    # ---------------------------------------------------------
    with tab4:
        st.subheader("🔄 Valutatore Scambi (Trade Analyzer)")
        t_col1, t_col2 = st.columns(2)

        with t_col1:
            squadra_A = st.selectbox(
                "La tua FantaSquadra:", lista_squadre, key="sq_A"
            )
            df_sq_A = df[
                df["FantaSquadra"].astype(str).str.strip() == squadra_A.strip()
            ]
            ceduti = st.multiselect(
                "Giocatori che CEDO:",
                options=df_sq_A["Calciatore"].tolist(),
                key="ceduti",
            )

        with t_col2:
            squadre_B_opts = [s for s in lista_squadre if s != squadra_A]
            squadra_B = st.selectbox(
                "FantaSquadra Avversaria:", squadre_B_opts, key="sq_B"
            )
            df_sq_B = df[
                df["FantaSquadra"].astype(str).str.strip() == squadra_B.strip()
            ]
            ricevuti = st.multiselect(
                "Giocatori che RICEVO:",
                options=df_sq_B["Calciatore"].tolist(),
                key="ricevuti",
            )

        if ceduti and ricevuti:
            df_c = df_sq_A[df_sq_A["Calciatore"].isin(ceduti)]
            df_r = df_sq_B[df_sq_B["Calciatore"].isin(ricevuti)]

            diff_fm = df_r["FantaMedia"].sum() - df_c["FantaMedia"].sum()
            diff_fvm = df_r["FVM"].sum() - df_c["FVM"].sum()

            st.markdown("### ⚖️ Bilancio Scambio")
            r1, r2 = st.columns(2)
            r1.metric("Delta FantaMedia Totale", f"{diff_fm:+.2f}")
            r2.metric("Delta FVM (Valore)", f"{diff_fvm:+.0f}")

    # ---------------------------------------------------------
    # TAB 5: REPORT & OTTIMIZZATORE
    # ---------------------------------------------------------
    with tab5:
        st.subheader("📄 Report & Formazione")
        if lista_squadre:
            squadra_rep = st.selectbox(
                "Seleziona FantaSquadra:", lista_squadre, key="rep_sq"
            )
            df_sq_rep = df[
                df["FantaSquadra"].astype(str).str.strip() == squadra_rep.strip()
            ]

            if not df_sq_rep.empty:
                xi, err_msg = calcola_miglior_xi(df_sq_rep, (3, 4, 3))
                if xi is not None:
                    st.markdown("### 🏟️ Top XI Consigliato (3-4-3)")
                    st.dataframe(
                        xi[
                            [
                                "Calciatore",
                                "Ruolo",
                                "Squadra",
                                "FantaMedia",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.warning(f"⚠️ Impossibile schierare il 3-4-3: {err_msg}")

    # ---------------------------------------------------------
    # TAB 6: SIMULATORE SCONTRI DIRETTI
    # ---------------------------------------------------------
    with tab_sim:
        st.subheader("⚔️ Simulatore Scontro Diretto")
        if len(lista_squadre) >= 2:
            s1, s2 = st.columns(2)
            with s1:
                sq_c = st.selectbox(
                    "Squadra Casa:", lista_squadre, index=0, key="sim_c"
                )
                mod_c = st.selectbox(
                    "Modulo Casa:",
                    ["3-4-3", "3-5-2", "4-3-3", "4-4-2"],
                    key="mod_c",
                )
            with s2:
                opts_f = [s for s in lista_squadre if s != sq_c]
                sq_f = st.selectbox(
                    "Squadra Trasferta:", opts_f, index=0, key="sim_f"
                )
                mod_f = st.selectbox(
                    "Modulo Trasferta:",
                    ["3-4-3", "3-5-2", "4-3-3", "4-4-2"],
                    key="mod_f",
                )

            if st.button("🚀 Simula Partita", use_container_width=True):
                df_c_sub = df[
                    df["FantaSquadra"].astype(str).str.strip() == sq_c.strip()
                ]
                df_f_sub = df[
                    df["FantaSquadra"].astype(str).str.strip() == sq_f.strip()
                ]

                xi_c, err_c = calcola_miglior_xi(
                    df_c_sub, tuple(map(int, mod_c.split("-")))
                )
                xi_f, err_f = calcola_miglior_xi(
                    df_f_sub, tuple(map(int, mod_f.split("-")))
                )

                if xi_c is not None and xi_f is not None:
                    p_c = xi_c["FM_clean"].sum() + 2.0  # +2 Bonus Casa
                    p_f = xi_f["FM_clean"].sum()
                    g_c, g_f = calcola_gol(p_c), calcola_gol(p_f)

                    st.markdown(
                        f"## 🏆 Risultato: **{sq_c} {g_c} - {g_f} {sq_f}**"
                    )
                    st.caption(
                        f"Punti Totali: {sq_c} ({p_c:.1f} con bonus casa) vs"
                        f" {sq_f} ({p_f:.1f})"
                    )
                else:
                    if err_c:
                        st.error(f"❌ Errore **{sq_c}**: {err_c}")
                    if err_f:
                        st.error(f"❌ Errore **{sq_f}**: {err_f}")
