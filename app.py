import pandas as pd
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Fanta Analyzer", page_icon="⚽", layout="wide"
)

st.title("⚽ Fanta Analyzer - Dashboard Lega Fantacalcio")
st.markdown("Analisi della lista calciatori e delle rose della tua lega.")

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
      # Legge la scheda 'Lista calciatori' se presente, altrimenti la prima scheda
      xls = pd.ExcelFile(uploaded_file)
      sheet = (
          "Lista calciatori"
          if "Lista calciatori" in xls.sheet_names
          else xls.sheet_names[0]
      )
      df = pd.read_excel(uploaded_file, sheet_name=sheet)

    # Mappatura automatica delle colonne dal file Fantacalcio
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
    st.sidebar.success(f"File caricato! ({len(df)} calciatori trovati)")

  except Exception as e:
    st.sidebar.error(f"Errore durante la lettura del file: {e}")

# 2. Gestione Dati e Filtri
if df is not None:
  st.sidebar.write("---")
  st.sidebar.header("🔍 Filtri Avanzati")

  df_filtrato = df.copy()

  # Filtro Stato Giocatore (Svincolati / Acquistati)
  if "FantaSquadra" in df.columns:
    stato_opzioni = ["Tutti", "Solo Svincolati", "Solo Acquistati"]
    stato_sel = st.sidebar.selectbox("Stato Calciatore", stato_opzioni)

    if stato_sel == "Solo Svincolati":
      df_filtrato = df_filtrato[df_filtrato["FantaSquadra"].isna()]
    elif stato_sel == "Solo Acquistati":
      df_filtrato = df_filtrato[df_filtrato["FantaSquadra"].notna()]

    # Filtro FantaSquadra specifica
    fantasquadre = ["Tutte"] + sorted(
        [
            str(x)
            for x in df["FantaSquadra"].dropna().unique()
            if str(x).strip() != ""
        ]
    )
    if len(fantasquadre) > 1 and stato_sel != "Solo Svincolati":
      fantasquadra_sel = st.sidebar.selectbox(
          "FantaSquadra della Lega", fantasquadre
      )
      if fantasquadra_sel != "Tutte":
        df_filtrato = df_filtrato[
            df_filtrato["FantaSquadra"].astype(str) == fantasquadra_sel
        ]

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

  # Ricerca per Nome Calciatore
  if "Calciatore" in df.columns:
    nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")
    if nome_cercato:
      df_filtrato = df_filtrato[
          df_filtrato["Calciatore"]
          .astype(str)
          .str.contains(nome_cercato, case=False)
      ]

  # 3. Metriche Chiave
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Calciatori Selezionati", len(df_filtrato))

  if "FantaMedia" in df_filtrato.columns:
    max_fm = df_filtrato["FantaMedia"].max() if not df_filtrato.empty else 0
    col2.metric("FantaMedia Max", round(float(max_fm), 2))

  if "Quotazione" in df_filtrato.columns:
    quot_med = df_filtrato["Quotazione"].mean() if not df_filtrato.empty else 0
    col3.metric("Quotazione Media", round(float(quot_med), 1))

  if "FVM" in df_filtrato.columns:
    fvm_max = df_filtrato["FVM"].max() if not df_filtrato.empty else 0
    col4.metric("FVM Max", int(fvm_max))

  st.write("---")

  # 4. Tabella Risultati
  st.subheader("📋 Lista e Statistiche Calciatori")

  # Mettiamo in ordine le colonne principali per la visualizzazione
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
  colonne_presenti = [c for c in colonne_prioritarie if c in df_filtrato.columns]
  altre_colonne = [c for c in df_filtrato.columns if c not in colonne_presenti]
  colonne_finali = colonne_presenti + altre_colonne

  st.dataframe(
      df_filtrato[colonne_finali], use_container_width=True, hide_index=True
  )

else:
  st.info(
      "👈 Carica il file `.xlsx` scaricato da Fantacalcio dalla barra laterale a"
      " sinistra per visualizzare la dashboard!"
  )
