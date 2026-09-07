import pandas as pd
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Fanta Analyzer", page_icon="⚽", layout="wide"
)

st.title("⚽ Fanta Analyzer - Dashboard Calciatori")
st.markdown("Analizza le statistiche dei giocatori per l'asta e la formazione.")

# Dati di prova di default
data_default = {
    "Calciatore": [
        "Lautaro Martinez",
        "Kvaratskhelia",
        "Barella",
        "Theo Hernandez",
        "Di Gregorio",
        "Calhanoglu",
        "Lookman",
        "Bremer",
        "Provedel",
        "Orsolini",
    ],
    "Squadra": [
        "Inter",
        "Napoli",
        "Inter",
        "Milan",
        "Juventus",
        "Inter",
        "Atalanta",
        "Juventus",
        "Lazio",
        "Bologna",
    ],
    "Ruolo": ["A", "A", "C", "D", "P", "C", "A", "D", "P", "C"],
    "Quotazione": [38, 32, 22, 19, 15, 25, 30, 16, 14, 20],
    "FantaMedia": [8.5, 8.1, 7.2, 6.8, 5.5, 7.8, 8.2, 6.6, 5.2, 7.4],
    "Gol": [24, 11, 4, 5, 0, 10, 17, 3, 0, 10],
    "Assist": [3, 6, 6, 4, 0, 8, 8, 0, 0, 4],
}

# Sidebar per il caricamento file
st.sidebar.header("📁 Carica Dati Reali")
uploaded_file = st.sidebar.file_uploader(
    "Carica listino (.csv o .xlsx)", type=["csv", "xlsx"]
)

df = None

if uploaded_file is not None:
  try:
    if uploaded_file.name.endswith(".csv"):
      # Prova a leggere prima con separatore virgola, poi con punto e virgola
      try:
        df = pd.read_csv(uploaded_file)
        if len(df.columns) <= 1:
          uploaded_file.seek(0)
          df = pd.read_csv(uploaded_file, sep=";")
      except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=";")
    else:
      df = pd.read_excel(uploaded_file)

    # Mappatura automatica colonne di Fantacalcio.it
    mappatura_colonne = {
        "Nome": "Calciatore",
        "R": "Ruolo",
        "R.": "Ruolo",
        "Qt.A": "Quotazione",
        "Qt. A": "Quotazione",
        "Qt.I": "Quotazione",
        "Fm": "FantaMedia",
        "FM": "FantaMedia",
        "Mv": "MediaVoto",
        "MV": "MediaVoto",
        "G": "Gol",
        "A": "Assist",
    }
    df = df.rename(columns=mappatura_colonne)

    st.sidebar.success("File caricato con successo!")
  except Exception as e:
    st.sidebar.error(f"Errore nella lettura del file: {e}")
    df = pd.DataFrame(data_default)
else:
  df = pd.DataFrame(data_default)

st.sidebar.write("---")

# Filtri
st.sidebar.header("🔍 Filtri di Ricerca")

if {"Ruolo", "Squadra", "Calciatore"}.issubset(df.columns):
  ruoli = ["Tutti"] + list(df["Ruolo"].dropna().astype(str).unique())
  ruolo_selezionato = st.sidebar.selectbox("Seleziona Ruolo", ruoli)

  squadre = ["Tutte"] + sorted(
      list(df["Squadra"].dropna().astype(str).unique())
  )
  squadra_selezionata = st.sidebar.selectbox("Seleziona Squadra", squadre)

  nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")

  df_filtrato = df.copy()

  if ruolo_selezionato != "Tutti":
    df_filtrato = df_filtrato[
        df_filtrato["Ruolo"].astype(str) == ruolo_selezionato
    ]

  if squadra_selezionata != "Tutte":
    df_filtrato = df_filtrato[
        df_filtrato["Squadra"].astype(str) == squadra_selezionata
    ]

  if nome_cercato:
    df_filtrato = df_filtrato[
        df_filtrato["Calciatore"]
        .astype(str)
        .str.contains(nome_cercato, case=False)
    ]

  # Metriche
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Giocatori Visualizzati", len(df_filtrato))

  if "FantaMedia" in df_filtrato.columns:
    col2.metric(
        "FantaMedia Max",
        (
            round(df_filtrato["FantaMedia"].max(), 2)
            if not df_filtrato.empty
            else 0
        ),
    )
  if "Quotazione" in df_filtrato.columns:
    col3.metric(
        "Quotazione Media",
        (
            round(df_filtrato["Quotazione"].mean(), 1)
            if not df_filtrato.empty
            else 0
        ),
    )
  if "Gol" in df_filtrato.columns:
    col4.metric(
        "Totale Gol", df_filtrato["Gol"].sum() if not df_filtrato.empty else 0
    )

  st.write("---")

  # Tabella
  st.subheader("📋 Lista Calciatori")
  st.dataframe(df_filtrato, use_container_width=True, hide_index=True)
else:
  st.warning(
      "Impossibile trovare le colonne necessarie. Colonne rilevate nel file:"
      f" `{list(df.columns)}`"
  )
