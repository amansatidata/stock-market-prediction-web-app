import streamlit as st
from datetime import date
import pandas as pd
import yfinance as yf
from prophet import Prophet
from prophet.plot import plot_plotly
from plotly import graph_objs as go
from sklearn.metrics import mean_absolute_percentage_error


# ── Configuration ─────────────────────────────────────────────────────────────

START = "2020-01-01"
TODAY = date.today().strftime("%Y-%m-%d")

st.title("📈 Stock Market Prediction App")

# Dropdown for stock selection
stocks = ("AAPL", "GOOG", "MSFT", "GME")
selected_stock = st.selectbox("Select dataset for prediction", stocks)

# Slider for prediction years
n_years = st.slider("Years of prediction:", 1, 6)
period = n_years * 365


# ── Data Loading ──────────────────────────────────────────────────────────────

@st.cache_data
def load_data(ticker):
    data = yf.download(ticker, START, TODAY)
    data.reset_index(inplace=True)
    return data


data_load_state = st.text("⏳ Loading data...")
data = load_data(selected_stock)
data_load_state.text(" Loading data... done!")

# Check if data is empty
if data.empty:
    st.error(" No data found for this stock or date range. Please try another one.")
    st.stop()

# Flatten MultiIndex columns if present
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)


# ── Display Raw Data ──────────────────────────────────────────────────────────

st.subheader("Raw data")
st.write(data.tail())


# ── Plot Raw Data ─────────────────────────────────────────────────────────────

def plot_raw_data():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Open"], name="Stock Open"))
    fig.add_trace(go.Scatter(x=data["Date"], y=data["Close"], name="Stock Close"))
    fig.layout.update(title_text="Time Series Data", xaxis_rangeslider_visible=True)
    st.plotly_chart(fig)


plot_raw_data()


# ── Prepare Data for Prophet ──────────────────────────────────────────────────

df_train = data[["Date", "Close"]].rename(columns={"Date": "ds", "Close": "y"})

# Ensure numeric values
df_train["y"] = pd.to_numeric(df_train["y"], errors="coerce")
df_train.dropna(subset=["y"], inplace=True)

if len(df_train) < 2:
    st.error(" Not enough numeric data to train the model.")
    st.stop()


# ── Train Prophet Model ───────────────────────────────────────────────────────

m = Prophet()
m.fit(df_train)


# ── Make Future Predictions ───────────────────────────────────────────────────

future = m.make_future_dataframe(periods=period)
forecast = m.predict(future)


# ── Model Accuracy (MAPE) ─────────────────────────────────────────────────────

# Compare Prophet's fitted values against actual historical closing prices
actual    = df_train["y"].values
predicted = forecast[forecast["ds"].isin(df_train["ds"])]["yhat"].values

mape = mean_absolute_percentage_error(actual, predicted) * 100

st.subheader("Model Performance")
col1, col2, col3 = st.columns(3)

col1.metric(
    label="In-sample MAPE",
    value=f"{mape:.2f}%",
    help="Mean Absolute Percentage Error on historical data. Lower is better."
)
col2.metric(
    label="Training rows",
    value=f"{len(df_train):,}",
    help="Number of daily closing price records used to train Prophet."
)
col3.metric(
    label="Forecast horizon",
    value=f"{n_years} yr{'s' if n_years > 1 else ''}",
    help="How far into the future the model is predicting."
)

if mape < 10:
    st.success(f"MAPE of {mape:.2f}% — strong in-sample fit for {selected_stock}.")
elif mape < 20:
    st.warning(f" MAPE of {mape:.2f}% — moderate fit. Treat long-range forecasts with caution.")
else:
    st.error(f"MAPE of {mape:.2f}% — high error. This stock may be too volatile for Prophet.")


# ── Display Forecast ──────────────────────────────────────────────────────────

st.subheader("Forecast data")
st.write(forecast.tail())

st.write("Forecast plot")
fig1 = plot_plotly(m, forecast)
st.plotly_chart(fig1)

st.write("Forecast components (Trend & Seasonality)")
fig2 = m.plot_components(forecast)
st.write(fig2)