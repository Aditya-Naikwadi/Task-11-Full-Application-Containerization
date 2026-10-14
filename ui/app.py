import os
import requests
import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Deep Learning Inference Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for aesthetics
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .prediction-box {
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Configuration from environment variables (overridden by Docker Compose to http://api:5000/predict)
DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:5000/predict")

# Sidebar Configuration
st.sidebar.image("https://img.icons8.com/clouds/200/brain.png", width=120)
st.sidebar.title("⚙️ Service Settings")
api_url = st.sidebar.text_input("Backend API Endpoint", value=DEFAULT_API_URL)

st.sidebar.markdown("---")
st.sidebar.subheader("System Health")
health_url = api_url.replace("/predict", "/health")
try:
    health_resp = requests.get(health_url, timeout=3)
    if health_resp.status_code == 200:
        st.sidebar.success("🟢 API Service Connected")
    else:
        st.sidebar.warning(f"🟡 API Status Code: {health_resp.status_code}")
except Exception:
    st.sidebar.error("🔴 API Service Offline")

st.sidebar.markdown("---")
st.sidebar.caption("Antigravity ML Engine • Production Ready Container")

# Main Interface
st.markdown('<div class="main-header">🧠 Deep Learning Inference System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Containerized Full-Stack AI Platform: Flask Microservice & Streamlit Interactive UI</div>', unsafe_allow_html=True)

# Input columns
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📊 Input Features")
    st.info("Tune the numerical input attributes below to generate real-time neural network predictions.")

    f1 = st.slider("Feature 1: Glucose / Level A", min_value=0.0, max_value=200.0, value=75.0, step=0.5)
    f2 = st.slider("Feature 2: Blood Pressure / Level B", min_value=0.0, max_value=150.0, value=80.0, step=0.5)
    f3 = st.slider("Feature 3: Body Mass Index / Level C", min_value=0.0, max_value=60.0, value=28.5, step=0.1)
    f4 = st.slider("Feature 4: Patient Age / Level D", min_value=1.0, max_value=100.0, value=45.0, step=1.0)

    # Optional manual numerical direct inputs in an expander
    with st.expander("📝 Direct Numerical Inputs / Batch Input"):
        f1_direct = st.number_input("Direct F1", value=float(f1))
        f2_direct = st.number_input("Direct F2", value=float(f2))
        f3_direct = st.number_input("Direct F3", value=float(f3))
        f4_direct = st.number_input("Direct F4", value=float(f4))

    # Prediction Action Button
    predict_clicked = st.button("🚀 Run Prediction", type="primary", use_container_width=True)

with col2:
    st.subheader("📈 Prediction & Analysis")

    if predict_clicked:
        # Construct feature vector
        features = [float(f1), float(f2), float(f3), float(f4)]
        payload = {"features": features}

        with st.spinner("Dispatching inference payload to Flask API..."):
            try:
                response = requests.post(api_url, json=payload, timeout=10)

                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status")

                    if status == "success":
                        label = result.get("label", "Unknown Class")
                        confidence = result.get("confidence", 0.0) * 100.0
                        probabilities = result.get("probabilities", [])
                        class_names = result.get("class_names", [f"Class {i}" for i in range(len(probabilities))])

                        # Display prediction banner
                        st.markdown(f"""
                        <div class="prediction-box">
                            <h3 style="margin:0; font-size: 1.1rem; opacity: 0.9;">Predicted Classification</h3>
                            <h1 style="margin: 0.5rem 0; font-size: 2.2rem; color: #FFFFFF;">{label}</h1>
                            <p style="margin:0; font-size: 1.1rem;">Confidence: <strong>{confidence:.2f}%</strong></p>
                        </div>
                        """, unsafe_allow_html=True)

                        # Detailed Probability Distribution
                        st.write("##### 📊 Class Probability Breakdown")
                        prob_df = pd.DataFrame({
                            "Class": class_names,
                            "Probability (%)": [p * 100 for p in probabilities]
                        })

                        st.bar_chart(prob_df.set_index("Class"), color="#3B82F6")

                        # Raw JSON Response display
                        with st.expander("🔍 View Raw API JSON Payload"):
                            st.json(result)

                    else:
                        st.error(f"Prediction failed with status: {status}")
                        st.json(result)

                else:
                    st.error(f"API Error (HTTP {response.status_code})")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.write(response.text)

            except requests.exceptions.ConnectionError:
                st.error(f"❌ Connection Failed: Could not reach the API at `{api_url}`.")
                st.warning("Ensure the Docker containers are running and that the network is configured correctly in `docker-compose.yml`.")
            except requests.exceptions.Timeout:
                st.error("⏳ Inference Request Timed Out (Exceeded 10 seconds).")
            except Exception as e:
                st.error(f"⚠️ Unexpected Client Error: {str(e)}")

    else:
        st.markdown("""
        <div style="background-color: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 12px; padding: 3rem; text-align: center; color: #64748B;">
            <h4 style="color: #475569;">Ready for Inference</h4>
            <p>Select your feature values on the left panel and click <strong>Run Prediction</strong> to submit the payload to the containerized deep learning microservice.</p>
        </div>
        """, unsafe_allow_html=True)
