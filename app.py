import pandas as pd
import streamlit as st

# Modulo di caricamento file nella sidebar
st.sidebar.header("📁 Carica Dati Reali")
uploaded_file = st.sidebar.file_uploader(
    "Carica il listino (.csv o .xlsx)", type=["csv", "xlsx"]
)

if uploaded_file is not None:
  if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
  else:
    df = pd.read_excel(uploaded_file)
  st.sidebar.success("File caricato con successo!")
else:
  # Se non carichi nulla, l'app usa i dati di prova predefiniti
  df = pd.DataFrame(data)
    
# Configurazione della pagina
st.set_page_config(
    page_title="Fanta Analyzer", page_icon="⚽", layout="wide"
)

st.title("⚽ Fanta Analyzer - Dashboard Calciatori")
st.markdown("Analizza le statistiche dei giocatori per l'asta e la formazione.")

# 1. Creazione di un dataset di prova (Mock Data)
data = {
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

df = pd.DataFrame(data)

# 2. Sidebar per i Filtri
st.sidebar.header("🔍 Filtri di Ricerca")

# Filtro Ruolo
ruoli = ["Tutti"] + list(df["Ruolo"].unique())
ruolo_selezionato = st.sidebar.selectbox("Seleziona Ruolo", ruoli)

# Filtro Squadra
squadre = ["Tutte"] + sorted(list(df["Squadra"].unique()))
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
      df_filtrato["Calciatore"].str.contains(nome_cercato, case=False)
  ]

# 3. Metriche Chiave (KPIs)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Giocatori Visualizzati", len(df_filtrato))
col2.metric(
    "FantaMedia Max",
    df_filtrato["FantaMedia"].max() if not df_filtrato.empty else 0,
)
col3.metric(
    "Quotazione Media",
    (
        round(df_filtrato["Quotazione"].mean(), 1)
        if not df_filtrato.empty
        else 0
    ),
)
col4.metric(
    "Totale Gol", df_filtrato["Gol"].sum() if not df_filtrato.empty else 0
)

st.write("---")

# 4. Tabella Dati Interattiva
st.subheader("📋 Lista Calciatori")
st.dataframe(
    df_filtrato,
    use_container_width=True,
    hide_index=True,
)

# 5. Grafico di analisi rapida
if not df_filtrato.empty:
  st.subheader("📊 Rapporto Quotazione / FantaMedia")
  st.bar_chart(df_filtrato.set_index("Calciatore")[["Quotazione", "FantaMedia"]])
