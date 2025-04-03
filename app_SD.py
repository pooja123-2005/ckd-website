import streamlit as st
import pandas as pd
import numpy as np
import pickle
import sqlite3
import bcrypt
import google.generativeai as genai
from catboost import CatBoostClassifier
from sklearn.ensemble import VotingClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier

# ✅ Configure Google Gemini AI
genai.configure(api_key="AIzaSyD8PP54XQM79srUJ6Zrngg32G16vS-6i-c")
model = genai.GenerativeModel("gemini-1.5-pro")

def get_health_precautions(patient_data):
    prompt = (f"Patient test results: {patient_data}. Based on these lab values, provide concise health precautions. "
              "Limit to 2-3 key points covering diet, hydration, and lifestyle. Keep it brief and patient-friendly.")
    response = model.generate_content(prompt)
    return response.text

# ✅ Database setup
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def register_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    hashed_pw = hash_password(password)
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password(password, user[0]):
        return True
    return False

# ✅ Initialize DB
init_db()

def main():
    st.set_page_config(page_title="CKD Prediction", page_icon="🩺", layout="wide")
    
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    menu = ["Home", "Login", "Sign Up"] if not st.session_state.authenticated else ["Home", "Logout"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    if choice == "Login":
        st.subheader("🔑 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if authenticate_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("✅ Logged in successfully!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
    
    elif choice == "Sign Up":
        st.subheader("📝 Create an Account")
        new_user = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Sign Up"):
            if register_user(new_user, new_password):
                st.success("✅ Account created! You can now log in.")
            else:
                st.error("❌ Username already taken. Try another one.")
    
    elif choice == "Logout":
        st.session_state.authenticated = False
        st.success("✅ Logged out successfully!")
        st.rerun()
    
    else:
        if not st.session_state.authenticated:
            st.warning("Please log in to access the CKD prediction tool.")
            return
        
        st.title("🔬 Chronic Kidney Disease Prediction")
        st.image("ckdimg.png",use_container_width=True)
        
        # ✅ User Inputs



        age = st.number_input('Age', min_value=0, max_value=120, value=50)
        bp = st.number_input('Blood Pressure (mmHg)', min_value=0, max_value=200, value=80)
        sg = st.number_input('Specific Gravity', min_value=1.000, max_value=1.030, value=1.015)
        al = st.number_input('Albumin', min_value=0, max_value=5, value=0)
        su = st.number_input('Sugar', min_value=0, max_value=5, value=0)
        pc = st.selectbox('Pus Cell', ['normal', 'abnormal'])
        pcc = st.selectbox('Pus Cell Clumps', ['present', 'notpresent'])
        ba = st.selectbox('Bacteria', ['present', 'notpresent'])
        bgr = st.number_input('Blood Glucose Random (mg/dl)', min_value=0, max_value=500, value=100)
        bu = st.number_input('Blood Urea (mg/dl)', min_value=0, max_value=300, value=30)
        sc = st.number_input('Serum Creatinine (mg/dl)', min_value=0.0, max_value=30.0, value=1.2)
        sod = st.number_input('Sodium (mEq/L)', min_value=0, max_value=200, value=135)
        pot = st.number_input('Potassium (mEq/L)', min_value=0.0, max_value=15.0, value=4.5)
        hemo = st.number_input('Hemoglobin (g/dl)', min_value=0.0, max_value=20.0, value=14.0)
        pcv = st.number_input('Packed Cell Volume', min_value=0, max_value=100, value=45)
        wc = st.number_input('White Blood Cell Count (cells/cumm)', min_value=0, max_value=50000, value=7500)
        htn = st.sidebar.selectbox('Hypertension', ['yes', 'no'])
        dm = st.sidebar.selectbox('Diabetes Mellitus', ['yes', 'no'])
        cad = st.sidebar.selectbox('Coronary Artery Disease', ['yes', 'no'])
        appet = st.sidebar.selectbox('Appetite', ['good', 'poor'])
        pe = st.sidebar.selectbox('Pedal Edema', ['yes', 'no'])
        ane = st.sidebar.selectbox('Anemia', ['yes', 'no'])
                
        # ✅ Create DataFrame
        data = { 'age': age, 'bp': bp, 'sg': sg, 'al': al, 'sugar': su,  'pc': pc, 'pcc': pcc, 'ba': ba, 'bgr': bgr, 'bu': bu, 'sc': sc, 'sod': sod, 'pot': pot, 'hemo': hemo, 'pcv': pcv, 'wc': wc,  'htn': htn, 'dm': dm, 'cad': cad, 'appet': appet, 'pe': pe, 'ane': ane }
        input_df = pd.DataFrame([data])
        
        # ✅ Load ML Model & Predictions
        try:
            with open('final_preds.pkl', 'rb') as f:
                final_preds = pickle.load(f)
        except FileNotFoundError:
            st.error("Final predictions file not found. Please generate and save it first.")
            st.stop()
        
        if st.button("🔍 Predict"):
            prediction = final_preds[0]  # Replace with actual model logic
            if prediction == 1:
                st.error('🚨 Positive: Chronic Kidney Disease Detected!')
            else:
                st.success('✅ Negative: No Chronic Kidney Disease Detected')
            
            # ✅ Generate Health Precautions
            patient_data_str = ', '.join([f"{key}: {value}" for key, value in data.items()])
            precautions = get_health_precautions(patient_data_str)
            st.subheader("🩺 Health Precautions")
            st.markdown(f"* {precautions}")

if __name__ == "__main__":
    main()
