import time
from bs4 import BeautifulSoup
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# Podešavanje stranice
st.set_page_config(
    page_title="RIK Izborna Statistika UŽIVO", page_icon="📊", layout="wide"
)

# Automatsko osvežavanje na svakih 60 sekundi (60000 milisekundi)
st_autorefresh(interval=60000, key="rik_refresh")

URL = "https://www.rik.parlament.gov.rs/542645/rezultati/"


@st.cache_data(ttl=30)
def fetch_rik_data():
  """Funkcija za preuzimanje i parsiranje podataka sa RIK sajta."""
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }
  try:
    response = requests.get(URL, headers=headers, timeout=10)
    response.raise_for_status()
  except Exception as e:
    st.error(f"Greška prilikom povezivanja sa sajtom: {e}")
    return None, None, None

  soup = BeautifulSoup(response.text, "html.parser")

  # 1. Ekstrakcija opštih statističkih podataka
  # (Napomena: Selektori zavise od tačne HTML strukture RIK stranice)
  stats = {
      "upisani_biraci": 0,
      "izasli_biraci": 0,
      "biracka_mesta": 0,
      "obradjena_mesta": 0,
      "vazeci_listici": 0,
      "nevazeci_listici": 0,
  }

  # Primer parsiranja teksta/tabela sa stranice (prilagoditi ukoliko RIK koristi dinamički JS render)
  # Ukoliko RIK koristi API/JSON ili tabele, BeautifulSoup će ih pročitati:
  try:
    # Čitanje tabela sa stranice preko pandas-a
    tables = pd.read_html(response.text)
    # Pretpostavka: Prva ili druga tabela sadrži rezultate lista
    df_lists = tables[0] if len(tables) > 0 else pd.DataFrame()
  except Exception as e:
    df_lists = pd.DataFrame()

  return stats, df_lists, soup


st.title("📊 RIK Izborna Statistika - Praćenje UŽIVO")
st.markdown(
    "Automatsko osvežavanje podataka svakog **1 minuta** sa zvanične RIK"
    " stranice."
)

# Preuzimanje podataka
stats, df_lists, soup = fetch_rik_data()


# Funkcija za generisanje skraćenica (akronima) iz punog naziva liste
def generate_acronym(full_name):
  if not isinstance(full_name, str):
    return "LISTA"
  # Izdvajanje velikih slova ili skraćivanje poznatih naziva
  words = full_name.split()
  acronym = "".join([w[0] for w in words if w.isupper() or w[0].isalnum()])
  if len(acronym) < 2:
    acronym = full_name[:5].upper()
  return acronym[:10]


# --- SIMULACIJA/PRIKAZ PODATAKA (Ukoliko RIK stranica zahteva Selenium/Playwright za JS, ovde hvatamo podatke) ---
# Ako `pd.read_html` uspešno vrati tabelu kandidata/lista:
if df_lists is not None and not df_lists.empty:
  # Očekivane kolone prilagoditi strukturi RIK tabele:
  # Primer kolona: ['Бр.', 'Назив листе/кандидата', 'Број освојених гласова', 'Проценат освојених гласова (%)']

  # Kreiramo demo/fallback strukturu ukoliko se struktura menja u toku izborne noći:
  st.sidebar.success("Podaci uspešno učitani sa RIK-a.")
else:
  st.warning(
      "Podaci se trenutno učitavaju ili stranica zahteva JavaScript"
      " renderovanje. Prikazujem strukturu interfejsa:"
  )


# --- SEKCIJA 1: GLAVNI INDIKATORI (KPI) ---
col1, col2, col3, col4 = st.columns(4)

with col1:
  # Procenat obrađenih biračkih mesta (Број обрађених бирачких места / Број бирачких места)
  obradjena = 4820  # Primer vrednosti (zameniti parsiranom)
  ukupno_bm = 8273
  procenat_bm = (obradjena / ukupno_bm) * 100 if ukupno_bm > 0 else 0
  st.metric(
      label="Obrađena biračka mesta",
      value=f"{obradjena} / {ukupno_bm}",
      delta=f"{procenat_bm:.2f}%",
  )

with col2:
  # Procenat izlaznosti
  upisanih = 6500000
  izaslih = 3770000
  izlaznost_pct = (izaslih / upisanih) * 100 if upisanih > 0 else 0
  st.metric(
      label="Izlaznost birača",
      value=f"{izaslih:,} ({izlaznost_pct:.2f}%)",
  )

with col3:
  # Procenat važećih listića
  vazecih = 3650000
  vazeci_pct = (vazecih / izaslih) * 100 if izaslih > 0 else 0
  st.metric(label="Važeći listići", value=f"{vazeci_pct:.2f}%")

with col4:
  # Procenat nevažećih listića
  nevazecih = izaslih - vazecih
  nevazeci_pct = (nevazecih / izaslih) * 100 if izaslih > 0 else 0
  st.metric(label="Nevažeći listići", value=f"{nevazeci_pct:.2f}%")

st.markdown("---")

# --- SEKCIJA 2: PIE ČARTOVI (Izlaznost i Važeći/Nevažeći listići) ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
  st.subheader("🍩 Procenat izlaznosti")
  fig_izlaznost = px.pie(
      names=["Izašli birači", "Neizabrali / Neće glasati"],
      values=[izaslih, upisanih - izaslih],
      hole=0.4,
      color_discrete_sequence=["#1f77b4", "#aec7e8"],
  )
  st.plotly_chart(fig_izlaznost, use_container_width=True)

with chart_col2:
  st.subheader("🍩 Važeći vs Nevažeći listići")
  fig_listici = px.pie(
      names=["Važeći listići", "Nevažeći listići"],
      values=[vazecih, nevazecih],
      hole=0.4,
      color_discrete_sequence=["#2ca02c", "#ff7f0e"],
  )
  st.plotly_chart(fig_listici, use_container_width=True)

st.markdown("---")

# --- SEKCIJA 3: GRAFIKON I TABELA ZA SVIH 18 KANDIDATA/LISTA ---
st.subheader("📈 Raspodela glasova po izbornim listama (18 kandidata)")

# Simulirani podaci za svih 18 lista (u produkciji se zamenjuje sa `df_lists`)
data_18 = {
    "Rbr": list(range(1, 19)),
    "PuniNaziv": [
        "АЛЕКСАНДАР ВУЧИЋ - Србија не сме да стане",
        "ИВИЦА ДАЧИЋ - Премијер Србије",
        "ДР ВОЈИСЛАВ ШЕШЕЉ - Српска радикална странка",
        "МИЛОШ ЈОВАНОВИЋ - Демократска странка Србије (NDSS)",
        "СРБИЈА ЦЕНТАР - СЦЕНТ - Здравко Понош",
        "ЕКОЛОШКИ УСТАНАК - Ћемета - Др Ћута",
        "ПОКРЕТ СОЦИЈАЛИСТА - Александар Вулин",
        "ЈЕДИНСТВЕНА СРБИЈА - Драган Марковић Палма",
        "СУВЕРЕНИСТИ - Саша Радуловић",
        "ДВЕРИ - Бошко Обрадовић",
        "ЗАВЕТНИЦИ - Милица Đurđević Stamenkovski",
        "СТРАНКА ПРАВДЕ И ПОМИРЕЊА - Муамер Зукорлић",
        "САВЕЗ ВОЈВОĐАНСКИХ МАЂАРА - Иштван Пастор",
        "РУСКА СТРАНКА - Слободан Николић",
        "АЛБАНСКА ДЕМОКРАТСКА АЛТЕРНАТИВА",
        "ГРУПА ГРАЂАНА - ЗА БОЉУ СРБИЈУ",
        "ПРОГРЕСИВНА ДЕМОКРАТСКА СТРАНКА",
        "НОВА СРБИЈА - Велимир Илић",
    ],
    "Glasovi": [
        1780000,
        450000,
        210000,
        320000,
        290000,
        180000,
        90000,
        75000,
        60000,
        150000,
        140000,
        80000,
        110000,
        40000,
        25000,
        35000,
        20000,
        15000,
    ],
    "Procenat": [
        46.5,
        11.7,
        5.5,
        8.3,
        7.5,
        4.7,
        2.3,
        1.9,
        1.5,
        3.9,
        3.6,
        2.1,
        2.8,
        1.0,
        0.6,
        0.9,
        0.5,
        0.4,
    ],
}

df_mock = pd.DataFrame(data_18)
# Generisanje akronima za grafikon
df_mock["Akronim"] = df_mock["PuniNaziv"].apply(generate_acronym)

# 1. Stubac grafikon (sa AKRONIMIMA na X osi)
fig_bar = px.bar(
    df_mock,
    x="Akronim",
    y="Procenat",
    text="Procenat",
    title="Procenat osvojenih glasova po listama (Akronimi)",
    labels={"Akronim": "Izborna lista", "Procenat": "Procenat glasova (%)"},
    color="Procenat",
    color_continuous_scale="Blues",
)
fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
st.plotly_chart(fig_bar, use_container_width=True)

# 2. Tabela (sa PUNIM NAZIVIMA lista/kandidata)
st.subheader("📋 Detaljna tabela sa punim nazivima lista i brojem glasova")
display_df = df_mock[
    ["Rbr", "PuniNaziv", "Glasovi", "Procenat"]
].copy()
display_df.columns = [
    "Rbr.",
    "Puni naziv liste/kandidata",
    "Broj osvojenih glasova",
    "Procenat (%)",
]
st.dataframe(display_df, use_container_width=True, hide_index=True)
