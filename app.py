import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
from datetime import datetime
import plotly.express as px

st.set_page_config(layout="wide")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bp_app.db", check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE,
                    password TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    age INTEGER,
                    weight INTEGER,
                    thyroid TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS bp_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_id INTEGER,
                    date TEXT,
                    time TEXT,
                    systolic INTEGER,
                    diastolic INTEGER,
                    pulse INTEGER,
                    medicine TEXT,
                    symptoms TEXT)""")

create_tables()

# ---------------- AUTH ----------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def login(email, password):
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    if user and verify_password(password, user[2]):
        return user
    return None

def signup(email, password):
    try:
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)",
                  (email, hash_password(password)))
        conn.commit()
        return True
    except:
        return False

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- LOGIN PAGE ----------------
if not st.session_state.user:
    st.title("💊 BP Tracker SaaS")

    menu = st.selectbox("Login / Signup", ["Login", "Signup"])

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if menu == "Login":
        if st.button("Login"):
            user = login(email, password)
            if user:
                st.session_state.user = user
                st.success("Logged in!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    else:
        if st.button("Signup"):
            if signup(email, password):
                st.success("Account created")
            else:
                st.error("User already exists")

    st.stop()

# ---------------- MAIN APP ----------------
st.sidebar.title("Menu")

page = st.sidebar.radio("Navigate", ["Dashboard", "Add Patient", "Log BP"])

user_id = st.session_state.user[0]

# ---------------- ADD PATIENT ----------------
if page == "Add Patient":
    st.title("👤 Add Patient")

    name = st.text_input("Name")
    age = st.number_input("Age", 1, 120)
    weight = st.number_input("Weight", 50, 300)
    thyroid = st.selectbox("Thyroid Issue", ["Yes", "No"])

    if st.button("Save Patient"):
        c.execute("INSERT INTO patients (user_id, name, age, weight, thyroid) VALUES (?, ?, ?, ?, ?)",
                  (user_id, name, age, weight, thyroid))
        conn.commit()
        st.success("Patient added!")

# ---------------- FETCH PATIENTS ----------------
c.execute("SELECT * FROM patients WHERE user_id=?", (user_id,))
patients = c.fetchall()

patient_dict = {p[2]: p[0] for p in patients}

# ---------------- LOG BP ----------------
if page == "Log BP":
    st.title("🩺 Log BP")

    if not patients:
        st.warning("Add patient first")
        st.stop()

    patient_name = st.selectbox("Select Patient", list(patient_dict.keys()))
    patient_id = patient_dict[patient_name]

    col1, col2 = st.columns(2)

    with col1:
        systolic = st.selectbox("Systolic", list(range(100, 201)))
        diastolic = st.selectbox("Diastolic", list(range(60, 141)))

    with col2:
        pulse = st.selectbox("Pulse", list(range(50, 121)))
        time = st.selectbox("Time", ["Morning", "Evening"])

    medicine = st.selectbox("Medicine Taken", ["Yes", "No"])
    symptoms = st.selectbox("Symptoms", ["None", "Headache", "Dizziness", "Chest Pain"])

    if st.button("Save BP"):
        c.execute("""INSERT INTO bp_logs 
                     (patient_id, date, time, systolic, diastolic, pulse, medicine, symptoms)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (patient_id, datetime.now().strftime("%Y-%m-%d"),
                   time, systolic, diastolic, pulse, medicine, symptoms))
        conn.commit()

        st.success("Saved!")

        # ALERT
        if systolic >= 180 or diastolic >= 120:
            st.error("🚨 CRITICAL BP! GO TO ER")

# ---------------- DASHBOARD ----------------
if page == "Dashboard":
    st.title("📊 Dashboard")

    if not patients:
        st.warning("Add patient first")
        st.stop()

    patient_name = st.selectbox("Select Patient", list(patient_dict.keys()))
    patient_id = patient_dict[patient_name]

    df = pd.read_sql_query("SELECT * FROM bp_logs WHERE patient_id=?", conn, params=(patient_id,))

    if df.empty:
        st.info("No data")
        st.stop()

    st.dataframe(df)

    # Chart
    fig = px.line(df, x="date", y=["systolic", "diastolic"], title="BP Trend")
    st.plotly_chart(fig, use_container_width=True)

    # Latest reading
    latest = df.iloc[-1]

    st.subheader("Latest Reading")
    st.write(f"Systolic: {latest['systolic']}")
    st.write(f"Diastolic: {latest['diastolic']}")

    if latest["systolic"] >= 180 or latest["diastolic"] >= 120:
        st.error("🚨 High Risk")