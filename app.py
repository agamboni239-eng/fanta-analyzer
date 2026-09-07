import pandas as pd
import streamlit as st

# Configurazione della pagina
st.set_page_config(
    page_title="Fanta Analyzer", page_icon="⚽", layout="wide"
)

st.title("⚽ Fanta Analyzer - Dashboard Calciatori")
st.markdown("Analizza le statistiche dei giocatori per l'asta e la formazione.")

# 1. Dati di prova (usati se non viene caricato nessun file)
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

# 2. Sidebar: Sezione caricamento File
st.sidebar.header("📁 Carica Dati Reali")
uploaded_file = st.sidebar.file_uploader(
    "Carica listino (.csv o .xlsx)", type=["csv", "xlsx"]
)

if uploaded_file is not None:
  try:
    if uploaded_file.name.endswith(".csv"):
      df = pd.read_csv(uploaded_file)
    else:
      df = pd.read_excel(uploaded_file)
    st.sidebar.success("File caricato con successo!")
  except Exception as e:
    st.sidebar.error("Errore nella lettura del file.")
    df = pd.DataFrame(data_default)
else:
  df = pd.DataFrame(data_default)

st.sidebar.write("---")

# 3. Sidebar: Filtri di Ricerca
st.sidebar.header("🔍 Filtri di Ricerca")

if {"Ruolo", "Squadra", "Calciatore"}.issubset(df.columns):
  # Filtro Ruolo
  ruoli = ["Tutti"] + list(df["Ruolo"].dropna().unique())
  ruolo_selezionato = st.sidebar.selectbox("Seleziona Ruolo", ruoli)

  # Filtro Squadra
  squadre = ["Tutte"] + sorted(list(df["Squadra"].dropna().unique()))
  squadra_selezionata = st.sidebar.selectbox("Seleziona Squadra", squadre)

  # Ricerca per Nome
  nome_cercato = st.sidebar.text_input("Cerca Calciatore", "")

  # Applicazione dei Filtri
  df_filtrato = df.copy()

  if ruolo_selezionato != "Tutti":
    df_filtrato = df_filtrato[df_filtrato["Ruolo"] == ruolo_selezionato]

  if squadra_selezionata != "Tutte":
    df_filtrato = df_filtrato[df_filtrato["Squadra"] == squadra_selezionata]

  if nome_cercato:
    df_filtrato = df_filtrato[
        df_filtrato["Calciatore"]
        .astype(str)
        .str.contains(nome_cercato, case=False)
    ]

  # 4. Metriche principali
  col1, col2, col3, col4 = st.columns(4)
  col1.metric("Giocatori Visualizzati", len(df_filtrato))

  if "FantaMedia" in df_filtrato.columns:
    col2.metric(
        "FantaMedia Max",
        df_filtrato["FantaMedia"].max() if not df_filtrato.empty else 0,
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

  # 5. Tabella Dati
  st.subheader("📋 Lista Calciatori")
  st.dataframe(
      df_filtrato,
      use_container_width=True,
      hide_index=True,
  )
else:
  st.warning(
      "Il file caricato non contiene le colonne minime richieste ('Calciatore',"
      " 'Squadra', 'Ruolo'). Controlla l'intestazione delle colonne nel tuo"
      " file!"
  )
