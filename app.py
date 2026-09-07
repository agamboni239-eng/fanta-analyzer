import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fanta Analyzer", page_icon="⚽")
st.title("⚽ Fanta Analyzer")
st.write("Benvenuto nel tuo tool personalizzato per il Fantacalcio!")

st.sidebar.header("Filtri")
ruolo = st.sidebar.selectbox("Seleziona Ruolo", ["Tutti", "P", "D", "C", "A"])
st.write(f"Ruolo selezionato: **{ruolo}**")
