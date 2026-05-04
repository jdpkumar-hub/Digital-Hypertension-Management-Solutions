import streamlit as st
import sqlite3
import pandas as pd
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import plotly.express as px

st.set_page_config(layout="wide")

# ---------------- EMAIL CONFIG ----------------
SENDER_EMAIL = "jdpkumar@gmail.com"
SENDER_PASSWORD = "jueq ezdw zlbi tkkx"

def send_otp(email, otp):
    msg = MIMEText(f"Your BP App OTP is {otp}")
    msg['Subject'] = "BP App Login OTP"
    msg['From'] = SENDER_EMAIL
    msg['To'] = email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

# ---------------- DATABASE ----------------
conn = sqlite3.connect("bp_app.db", check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE)""")

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

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if "otp" not in st.session_state:
    st.session_state.otp = None

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("📱 BP Tracker Login")

    email = st.text_input("Enter Email")

    if st.button("Send OTP"):
        otp = str(random.randint(100000, 999999))
        st.session_state.otp = otp
        st.session_state.email = email

        send_otp(email, otp)
        st.success("OTP sent to your email")

    otp_input = st.text_input("Enter OTP")

    if st.button("Verify"):
        if otp_input == st.session_state.otp:
            st.session_state.user = st.session_state.email
            st.success("Logged in!")
            st.rerun()
        else:
            st.error("Invalid OTP")

    st.stop()

# ---------------- GET USER ----------------
c.execute("SELECT id FROM users WHERE email=?", (st.session_state.user,))
user = c.fetchone()

if not user:
    c.execute("INSERT INTO users (email) VALUES (?)", (st.session_state.user,))
    conn.commit()
    user_id = c.lastrowid
else:
    user_id = user[0]

# ---------------- UI STYLE ----------------
st.markdown("""
<style>
.stButton button {
    height: 55px;
    font-size: 18px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("📊 Menu")
page = st.sidebar.radio("", ["Dashboard", "Add Patient", "Log BP"])

# ---------------- ADD PATIENT ----------------
if page == "Add Patient":
    st.title("👤 Add Patient")

    name = st.text_input("Name")
    age = st.number_input("Age", 1, 120)
    weight = st.number_input("Weight (lb)", 50, 300)
    thyroid = st.selectbox("Thyroid Issue", ["Yes", "No"])

    if st.button("Save Patient", use_container_width=True):
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
        systolic = st.selectbox("⬆️ Systolic", list(range(100, 201)))

    with col2:
        diastolic = st.selectbox("⬇️ Diastolic", list(range(60, 141)))

    pulse = st.selectbox("❤️ Pulse", list(range(50, 121))
)
    time = st.selectbox("Time", ["Morning", "Evening"])
    medicine = st.selectbox("Medicine Taken", ["Yes", "No"])
    symptoms = st.selectbox("Symptoms", ["None", "Headache", "Dizziness", "Chest Pain"])

    if st.button("💾 Save Reading", use_container_width=True):
        # Security check
        c.execute("SELECT id FROM patients WHERE id=? AND user_id=?", (patient_id, user_id))
        if not c.fetchone():
            st.error("Unauthorized")
            st.stop()

        c.execute("""INSERT INTO bp_logs 
                     (patient_id, date, time, systolic, diastolic, pulse, medicine, symptoms)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (patient_id, datetime.now().strftime("%Y-%m-%d"),
                   time, systolic, diastolic, pulse, medicine, symptoms))
        conn.commit()

        st.success("Saved!")

        # Alerts
        if systolic >= 180 or diastolic >= 120:
            st.error("🚨 EMERGENCY BP! GO TO HOSPITAL")
        elif systolic > 140:
            st.warning("⚠️ High BP")
        else:
            st.success("✅ Normal")

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

    fig = px.line(df, x="date", y=["systolic", "diastolic"], title="BP Trend")
    st.plotly_chart(fig, use_container_width=True)

    latest = df.iloc[-1]

    st.subheader("Latest Reading")
    st.write(f"Systolic: {latest['systolic']}")
    st.write(f"Diastolic: {latest['diastolic']}")

    if latest["systolic"] >= 180 or latest["diastolic"] >= 120:
        st.error("🚨 High Risk")