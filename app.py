import streamlit as st
import pandas as pd
import joblib
import numpy as np

# ============================================
# PAGE SETTINGS
# ============================================
st.set_page_config(page_title="Corporate Loan Risk AI", layout="centered")

# ============================================
# LOAD ASSETS
# ============================================
@st.cache_resource
def load_assets():
    try:
        model = joblib.load("extra_trees_model.pkl")
        # This is the file that fixes the 'Finance' error
        encoder = joblib.load("Financial_Risk_Label_Encoder.pkl")
        return model, encoder
    except Exception as e:
        st.error(f"Error loading files: {e}")
        return None, None

model, encoder = load_assets()

if model is None:
    st.stop()

# ============================================
# UI & INPUTS
# ============================================
st.title("Corporate Loan Risk AI")
st.markdown("---")


st.header("Financial Metrics")
col1, col2 = st.columns(2)

with col1:
    total_assets = st.number_input("Total Assets ($)", min_value=0.0, value=1000000.0)
    total_liabilities = st.number_input("Total Liabilities ($)", min_value=0.0, value=100000.0)
    revenue = st.number_input("Revenue ($)", min_value=0.0, value=2000000.0)
    current_assets = st.number_input("Current Assets ($)", min_value=0.0, value=500000.0)

with col2:
    cash_flow = st.number_input("Cash Flow ($)", value=100000.0)
    net_income = st.number_input("Net Income ($)", value=50000.0)
    operating_income = st.number_input("Operating Income ($)", value=75000.0)
    current_liabilities = st.number_input("Current Liabilities ($)", min_value=0.0, value=250000.0)

# ============================================
# PREDICTION LOGIC
# ============================================
if st.button("Analyze Financial Health", type="primary"):
    try:
        # 1. Calculate derived metrics
        equity = total_assets - total_liabilities
        debt_equity_ratio = total_liabilities / equity if equity > 0 else 999.0

        # 2. Assemble the 9 Features
        # Order must match exactly: Total_Assets, Total_Liabilities, Current_Assets, Current_Liabilities, Net_Income, Revenue, Operating_Income, Cash_Flow, Debt_Equity_Ratio
        feature_data = [
            total_assets,
            total_liabilities,
            current_assets,
            current_liabilities,
            net_income,
            revenue,
            operating_income,
            cash_flow,
            debt_equity_ratio
        ]

        # 4. Predict
        # We wrap it in [feature_data] to make it a 2D array
        prediction = model.predict([feature_data])

        # ====================================
        # RESULTS DISPLAY
        # ====================================
        st.markdown("---")
        st.subheader("Analysis Result")
        
        # In this dataset: 0 = Low Risk (Good), 1 = High Risk (Bad).
        if prediction[0] == 0:
            st.success("### STATUS: LOWER RISK (GOOD)")
            st.balloons()
        else:
            st.error("### STATUS: HIGHER RISK (BAD)")

        # Summary Metrics
        st.markdown("---")
        st.write(f"**Calculated Debt-Equity Ratio:** {debt_equity_ratio:.2f}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Assets", f"${total_assets:,.0f}")
        c2.metric("Liabilities", f"${total_liabilities:,.0f}")
        c3.metric("Revenue", f"${revenue:,.0f}")

    except Exception as e:
        st.error(f"Prediction Error: {e}")