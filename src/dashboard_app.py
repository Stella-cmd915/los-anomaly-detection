import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "logs.db")

st.set_page_config(page_title="Log Anomaly Dashboard", layout="wide")

st.title("Dashboard ανίχνευσης ανωμαλιών σε logs")

@st.cache_data(ttl=2)
def load_data():
    conn = sqlite3.connect(DB_PATH)

    q = """
    SELECT 
      p.id AS parsed_id,
      p.level,
      p.component,
      p.content,
      r.raw,
      pr.model_name,
      pr.score,
      pr.label,
      pr.infer_ms,
      pr.created_ts
    FROM predictions pr
    JOIN logs_parsed p ON p.id = pr.parsed_id
    JOIN logs_raw r ON r.id = p.raw_id
    ORDER BY pr.score DESC
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

df = load_data()

st.caption(f"Βάση: {DB_PATH} , εγγραφές: {len(df)}")

col1, col2, col3, col4 = st.columns(4)
models = sorted(df["model_name"].unique().tolist())
levels = sorted(df["level"].dropna().unique().tolist())
components = sorted(df["component"].dropna().unique().tolist())

with col1:
    model_sel = st.selectbox("Model", options=["ALL"] + models, index=0)
with col2:
    label_sel = st.selectbox("Label", options=["ALL", "anomaly", "normal"], index=1)
with col3:
    level_sel = st.multiselect("Level", options=levels, default=levels)
with col4:
    comp_sel = st.multiselect("Component", options=components, default=components[: min(8, len(components))])

f = df.copy()
if model_sel != "ALL":
    f = f[f["model_name"] == model_sel]
if label_sel != "ALL":
    f = f[f["label"] == label_sel]
if level_sel:
    f = f[f["level"].isin(level_sel)]
if comp_sel:
    f = f[f["component"].isin(comp_sel)]

st.subheader("Σύνοψη")
c1, c2, c3 = st.columns(3)
c1.metric("Συνολικές εγγραφές", len(f))
c2.metric("Anomalies", int((f["label"] == "anomaly").sum()))
c3.metric("Μέση καθυστέρηση infer (ms)", round(float(f["infer_ms"].mean()), 3) if len(f) else 0.0)

st.subheader("Κατανομή anomalies ανά component")
anom = f[f["label"] == "anomaly"]
if len(anom):
    grp = anom.groupby("component")["parsed_id"].count().sort_values(ascending=False).head(12)
    st.bar_chart(grp)
else:
    st.info("Δεν υπάρχουν anomalies με τα τρέχοντα φίλτρα.")

st.subheader("Λίστα εγγραφών και drill down")
show_cols = ["parsed_id", "model_name", "score", "label", "level", "component", "infer_ms", "created_ts"]
st.dataframe(f[show_cols].head(50), use_container_width=True)

pick = st.number_input("Δώσε parsed_id για λεπτομέρειες", min_value=int(f["parsed_id"].min()) if len(f) else 1, value=int(f["parsed_id"].min()) if len(f) else 1)
row = f[f["parsed_id"] == pick].head(1)

if len(row):
    st.markdown("### Λεπτομέρειες")
    st.write("Model:", row["model_name"].iloc[0], "Score:", float(row["score"].iloc[0]), "Label:", row["label"].iloc[0])
    st.code(row["raw"].iloc[0], language="text")
    st.write("Parsed content:")
    st.write(row["content"].iloc[0])
else:
    st.warning("Δεν βρέθηκε εγγραφή με αυτό το parsed_id στα τρέχοντα φίλτρα.")