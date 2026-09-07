import io
import pandas as pd
import plotly.express as px
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Fanta Analyzer", page_icon="⚽", layout="wide"
)

st.title("⚽ Fanta Analyzer - Dashboard Lega")

# 1. Sidebar: Caricamento File
st.sidebar.header("📁 Carica Listone / File Lega")
uploaded_file = st.sidebar.file_uploader(
    "Carica file Excel (.xlsx) o CSV", type=["xlsx", "csv"]
)

df = None

if uploaded_file is not None:
  try:
    if uploaded_file.name.endswith(".csv"):
      try:
        df = pd.read_csv(uploaded_file)
        if len(df.columns) <= 1:
          uploaded_file.seek(0)
          df = pd.read_csv(uploaded_file, sep=";")
      except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=";")
    else:
      xls = pd.ExcelFile(uploaded_file)
      sheet = (
          "Lista calciatori"
          if "Lista calciatori" in xls.sheet_names
          else xls.sheet_names[0]
      )
      df = pd.read_excel(uploaded_file, sheet_name=sheet)

    # Mappatura colonne
    mappatura = {
        "Nome": "Calciatore",
        "Sq.": "Squadra",
        "R.": "Ruolo",
        "QUOT.": "Quotazione",
        "FM": "FantaMedia",
        "MV": "MediaVoto",
        "PGv": "PartiteVoto",
        "FVM/1000": "FVM",
    }
    df = df.rename(columns=mappatura)
    st.sidebar.success(f"File caricato! ({len(df)} calciatori)")

  except Exception as e:
    st.sidebar.error(f"Errore caricamento: {e}")

if df is not None:
  st.sidebar.write("---")
  st.sidebar.header("🔍 Filtri Avanzati")

  df_filtrato = df.copy()

  # Lista FantaSquadre e filtro
  if "FantaSquadra" in df.columns:
    stato_opzioni = ["Tutti", "Solo Svincolati", "Solo Acquistati"]
    stato_sel = st.sidebar.selectbox("Stato Calciatore", stato_opzioni)

    if stato_sel == "Solo Svincolati":
      df_filtrato = df_filtrato[df_filtrato["FantaSquadra"].isna()]
    elif stato_sel == "Solo Acquistati":
      df_filtrato = df_filtrato[df_filtrato["FantaSquadra"].notna()]

    fantasquadre = sorted(
        [
            str(x)
            for x in df["FantaSquadra"].dropna().unique()
            if str(x).strip() != ""
        ]
    )
    fantasquadre_filtro = ["Tutte"] + fantasquadre
    if len(fantasquadre) > 0 and stato_sel != "Solo Svincolati":
      fantasquadra_sel = st.sidebar.selectbox(
          "FantaSquadra della Lega", fantasquadre_filtro
      )
      if fantasquadra_sel != "Tutte":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].astype(str) == fantasquadra_sel
        ]
  else:
    fantasquadre = []

  # Filtro Ruolo Classic
  if "Ruolo" in df.columns:
    ruoli = ["Tutti"] + list(df["Ruolo"].dropna().astype(str).unique())
    ruolo_sel = st.sidebar.selectbox("Ruolo Classic", ruoli)
    if ruolo_sel != "Tutti":
      df_filtrato = df_filtrato[df_filtrato["Ruolo"].astype(str) == ruolo_sel]

  # Filtro Squadra Serie A
  if "Squadra" in df.columns:
    squadre = ["Tutte"] + sorted(
        list(df["Squadra"].dropna().astype(str).unique())
    )
    squadra_sel = st.sidebar.selectbox("Squadra Serie A", squadre)
    if squadra_sel != "Tutte":
      df_filtrato = df_filtrato[
          df_filtrato["Squadra"].astype(str) == squadra_sel
      ]

  # Ricerca per Nome
  if "Calciatore" in df.columns:
    nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")
    if nome_cercato:
      df_filtrato = df_filtrato[
          df_filtrato["Calciatore"]
          .astype(str)
          .str.contains(nome_cercato, case=False)
      ]

  # Tab dell'app
  tab1, tab2, tab3, tab4, tab5 = st.tabs([
      "📋 Lista Calciatori",
      "📊 Grafico Occasioni",
      "🛡️ Analisi Rose Lega",
      "🔄 Valutatore Scambi",
      "📄 Report & Formazione",
  ])

  # TAB 1: LISTA GENERALE
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
        "R.MANTRA",
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

  # TAB 2: GRAFICO OCCASIONI
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

  # TAB 3: ANALISI ROSE LEGA
  with tab3:
    st.subheader("🛡️ Analisi Dettagliata Rosa FantaSquadra")

    if fantasquadre:
      squadra_scelta = st.selectbox(
          "Seleziona la FantaSquadra da analizzare:",
          fantasquadre,
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

    else:
      st.info("Nessuna FantaSquadra trovata nel file.")

  # TAB 4: VALUTATORE DI SCAMBI
  with tab4:
    st.subheader("🔄 Valutatore Scambi (Trade Analyzer)")
    st.markdown(
        "Seleziona i giocatori coinvolti nello scambio per simularne l'impatto"
        " sulla tua rosa."
    )

    t_col1, t_col2 = st.columns(2)

    with t_col1:
      st.markdown("### 🅰️ Giocatori che CEDO")
      squadra_A = st.selectbox(
          "Seleziona la tua FantaSquadra:",
          fantasquadre,
          key="sq_A",
      )
      df_squadra_A = df[df["FantaSquadra"].astype(str) == squadra_A]
      giocatori_ceduti = st.multiselect(
          "Seleziona i giocatori che vuoi scambiare:",
          options=df_squadra_A["Calciatore"].tolist(),
          key="ceduti",
      )

    with t_col2:
      st.markdown("### 🅱️ Giocatori che RICEVO")
      squadre_B_opts = [s for s in fantasquadre if s != squadra_A]
      squadra_B = st.selectbox(
          "Seleziona la FantaSquadra avversaria:",
          squadre_B_opts,
          key="sq_B",
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
      fvm_ricevuto = df_ricevuti["FVM"].sum() if "FVM" in df_ricevuti else 0
      diff_fvm = fvm_ricevuto - fvm_ceduto

      st.markdown("### ⚖️ Bilancio dello Scambio")

      res_col1, res_col2, res_col3 = st.columns(3)
      res_col1.metric("Delta FantaMedia Totale", f"{diff_fm:+.2f}")
      res_col2.metric("Delta Quotazione Totale", f"{diff_quot:+.0f}")
      res_col3.metric("Delta FVM (FantaValorMedio)", f"{diff_fvm:+.0f}")

      if diff_fm > 0 and diff_fvm >= 0:
        st.success(
            "🟢 **Scambio Vantaggioso:** Ottieni un guadagno sia in FantaMedia"
            " che in valore complessivo!"
        )
      elif diff_fm < 0 and diff_fvm < 0:
        st.error(
            "🔴 **Scambio Svantaggioso:** Perdi sia FantaMedia che valore di"
            " rosa."
        )
      else:
        st.warning(
            "🟡 **Scambio Equilibrato / Strategico:** Stai scambiando valore per"
            " titolarità o ridistribuendo i ruoli tra i reparti."
        )

      c_det1, c_det2 = st.columns(2)
      cols_show = [
          c
          for c in [
              "Calciatore",
              "Ruolo",
              "Squadra",
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

    else:
      st.info(
          "Seleziona almeno un giocatore da cedere e uno da ricevere per"
          " visualizzare l'analisi dello scambio."
      )

  # TAB 5: REPORT & OTTIMIZZATORE MODULO
  with tab5:
    st.subheader("📄 Report & Ottimizzatore Modulo (con Modificatore Difesa)")
    st.markdown(
        "L'algoritmo valuta tutti i moduli consentiti (3-4-3, 3-5-2, 4-3-3,"
        " 4-4-2, 4-5-1, 5-3-2, 5-4-1) e calcola il bonus atteso del"
        " **Modificatore Difesa** per identificare l'XI titolare più potente."
    )

    if fantasquadre:
      rep_col1, rep_col2 = st.columns([2, 1])

      with rep_col1:
        squadra_rep = st.selectbox(
            "Seleziona FantaSquadra:",
            fantasquadre,
            key="rep_sq",
        )

      with rep_col2:
        usa_modificatore = st.checkbox(
            "Attiva Modificatore Difesa",
            value=True,
            help=(
                "Si attiva con difesa a 4 o 5. Calcola il bonus in base alla"
                " MediaVoto del portiere e dei 3 migliori difensori."
            ),
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

        # Moduli ammessi
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

          # Calcolo Modificatore Difesa (se d_c >= 4)
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

          # KPI Modulo Consigliato
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

          # Tabella di confronto tra i moduli
          st.markdown("### 📊 Confronto Rendimento Moduli Tattici")
          st.dataframe(
              df_moduli[
                  ["Modulo", "Base FM", "Bonus Modificatore", "Punteggio Totale Atteso"]
              ],
              use_container_width=True,
              hide_index=True,
          )

          # Formazione IdealeSchierata
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
                  "FantaMedia",
                  "MediaVoto",
                  "PartiteVoto",
                  "Costo",
              ]
              if c in top_11.columns
          ]
          st.dataframe(
              top_11[cols_rep], use_container_width=True, hide_index=True
          )

          # Download File Excel
          output = io.BytesIO()
          with pd.ExcelWriter(output, engine="openpyxl") as writer:
            top_11[cols_rep].to_excel(
                writer, index=False, sheet_name=f"Top XI {miglior_modulo['Modulo']}"
            )
            df_moduli[
                ["Modulo", "Base FM", "Bonus Modificatore", "Punteggio Totale Atteso"]
            ].to_excel(writer, index=False, sheet_name="Confronto Moduli")
            df_squadra_rep[cols_rep].to_excel(
                writer, index=False, sheet_name="Rosa Completa"
            )
          excel_data = output.getvalue()

          st.download_button(
              label=f"📥 Scarica Report Excel ({squadra_rep})",
              data=excel_data,
              file_name=f"Report_{squadra_rep}.xlsx",
              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          )
    else:
      st.info("Nessuna FantaSquadra trovata per generare il report.")

else:
  st.info(
      "👈 Carica il file `.xlsx` scaricato da Leghe Fantacalcio dalla barra"
      " laterale!"
  )
