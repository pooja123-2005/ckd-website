import streamlit as st
import pandas as pd
import pickle
import sqlite3
import bcrypt
import google.generativeai as genai

# ---------------- CONFIG ---------------- #
st.set_page_config(page_title="CKD Prediction", layout="wide")
genai.configure(api_key="AIzaSyD8PP54XQM79srUJ6Zrngg32G16vS-6i-c")  # Replace with your key
model = genai.GenerativeModel("gemini-1.5-pro")

# ---------------- FUNCTIONS ---------------- #
def get_health_precautions(patient_data):
    prompt = (f"Patient test results: {patient_data}. Based on these lab values, provide concise health precautions. "
              "Limit to 2-3 key points covering diet, hydration, and lifestyle. Keep it brief and patient-friendly.")
    response = model.generate_content(prompt)
    return response.text

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )""")
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
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user and check_password(password, user[0])

# ---------------- UI ---------------- #
init_db()

def main():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    menu = ["Home", "Login", "Sign Up"] if not st.session_state.authenticated else ["Home", "Logout"]
    left, right = st.columns([1, 3])

    # -------- LEFT SIDE -------- #
    with left:
        choice = st.selectbox("🏠 Menu", menu)

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
                    st.error("❌ Username already taken.")

        elif choice == "Logout":
            st.session_state.authenticated = False
            st.success("✅ Logged out successfully!")
            st.rerun()

        if choice == "Home" and st.session_state.authenticated:
            st.subheader("🔮 Prediction Section")

            if st.button("Predict"):
                try:
                    with open('final_preds.pkl', 'rb') as f:
                        final_preds = pickle.load(f)
                except FileNotFoundError:
                    st.error("Final predictions file not found. Please generate and save it first.")
                    st.stop()

                input_df = pd.DataFrame([st.session_state.inputs])
                prediction = final_preds[0]

                st.subheader("🔍 Prediction Result")
                if prediction == 1:
                    st.error("🚨 Positive: Chronic Kidney Disease Detected!")
                    st.error("*🚨 Please consult a doctor immediately !!!*")
                else:
                    st.success("✅ Negative: No Chronic Kidney Disease Detected")

                st.subheader("🩺 Health Precautions")
                patient_data_str = ', '.join([f"{k}: {v}" for k, v in st.session_state.inputs.items()])
                precautions = get_health_precautions(patient_data_str)
                
                # ✅ FIXED OUTPUT: No extra bullets
                st.markdown(precautions.strip())

    # -------- RIGHT SIDE -------- #
    with right:
        if choice == "Home" and st.session_state.authenticated:
            st.title("🔬 Chronic Kidney Disease Prediction")
            st.image("ckdimg.png", use_column_width=True)

            col1, col2 = st.columns(2)
            with col1:
                age = st.number_input('Age', 0, 120, 50)
                bp = st.number_input('Blood Pressure (mmHg)', 0, 200, 80)
                sg = st.number_input('Specific Gravity', 1.000, 1.030, 1.015)
                al = st.number_input('Albumin', 0, 5, 0)
                su = st.number_input('Sugar', 0, 5, 0)
                pc = st.selectbox('Pus Cell', ['normal', 'abnormal'])
                pcc = st.selectbox('Pus Cell Clumps', ['present', 'notpresent'])
                ba = st.selectbox('Bacteria', ['present', 'notpresent'])
                bgr = st.number_input('Blood Glucose Random (mg/dl)', 0, 500, 100)
                bu = st.number_input('Blood Urea (mg/dl)', 0, 300, 30)

            with col2:
                sc = st.number_input('Serum Creatinine (mg/dl)', 0.0, 30.0, 1.2)
                sod = st.number_input('Sodium (mEq/L)', 0, 200, 135)
                pot = st.number_input('Potassium (mEq/L)', 0.0, 15.0, 4.5)
                hemo = st.number_input('Hemoglobin (g/dl)', 0.0, 20.0, 14.0)
                pcv = st.number_input('Packed Cell Volume', 0, 100, 45)
                wc = st.number_input('White Blood Cell Count', 0, 50000, 7500)
                htn = st.selectbox('Hypertension', ['yes', 'no'])
                dm = st.selectbox('Diabetes Mellitus', ['yes', 'no'])
                cad = st.selectbox('Coronary Artery Disease', ['yes', 'no'])
                appet = st.selectbox('Appetite', ['good', 'poor'])
                pe = st.selectbox('Pedal Edema', ['yes', 'no'])
                ane = st.selectbox('Anemia', ['yes', 'no'])

            st.session_state.inputs = {
                'age': age, 'bp': bp, 'sg': sg, 'al': al, 'sugar': su,
                'pc': pc, 'pcc': pcc, 'ba': ba, 'bgr': bgr, 'bu': bu,
                'sc': sc, 'sod': sod, 'pot': pot, 'hemo': hemo,
                'pcv': pcv, 'wc': wc, 'htn': htn, 'dm': dm,
                'cad': cad, 'appet': appet, 'pe': pe, 'ane': ane
            }
        elif choice == "Home" and not st.session_state.authenticated:
            st.warning("🔒 Please log in to access the CKD prediction form.")

    # -------- Footer -------- #
    st.markdown("""<hr style="margin-top: 2em;">""", unsafe_allow_html=True)
    st.markdown("Mentors: <b>Sumana Das</b> |[🔗 LinkedIn](https://www.linkedin.com/search/results/all/?heroEntityKey=urn%3Ali%3Afsd_profile%3AACoAAAIwVBYBJTLkL5coXl4BYqE3spJc2ey2xV8&keywords=SUMANA%20DAS&origin=ENTITY_SEARCH_HOME_HISTORY&sid=_Yb) ,<b> Aparna Tanam</b> | 🔗 [LinkedIn](https://in.linkedin.com/in/aparna-tanam-42532929)",unsafe_allow_html=True)
    st.markdown("Made by : <b>Methuku Divyasri</b> | [🔗 LinkedIn](https://www.linkedin.com/in/methuku-divyasri-834b64278/) , <b>Garlapad Akshara</b> | [🔗 LinkedIn](https://www.linkedin.com/search/results/all/?fetchDeterministicClustersOnly=true&heroEntityKey=urn%3Ali%3Afsd_profile%3AACoAAEjBC1MB9SooWJfOxV0bOlDjZ6HKPPhrwz0&keywords=akshara%20garlapad&origin=RICH_QUERY_TYPEAHEAD_HISTORY&position=0&searchId=501d8acb-0621-4cac-beb0-94dba8d9e5e1&sid=0Mo&spellCorrectionEnabled=true) ,<b> Poojitha Kottam</b> | [🔗 LinkedIn](https://in.linkedin.com/in/poojitha-kottam-2064b5255?original_referer=https%3A%2F%2Fwww.google.com%2F)", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
