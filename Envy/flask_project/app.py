from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import numpy as np

app = Flask(__name__)

# Global variable to store EPS values

def get_eps_data(ticker):
    """
    Fetches EPS data for the given ticker from Macrotrends and stores it in the global epsValues array.
    """
    global epsValues  # Refer to the global variable
    url = f"https://www.macrotrends.net/stocks/charts/{ticker}/any-company/eps-earnings-per-share-diluted"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", {"class": "historical_data_table table"})
    if not tables:
        return f"Unable to locate EPS table for ticker {ticker}."
    
    rows = tables[0].find_all("tr")[1:]  # Skip header row
    eps_values_local = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            eps_text = cols[1].text.strip()
            try:
                eps = float(eps_text.replace("$", "").replace(",", ""))
                eps_values_local.append(eps)
            except ValueError:
                continue
    
    if eps_values_local:
        epsValues.clear()
        epsValues.extend(eps_values_local[:7])
        epsValues.reverse()
    else:
        return f"No valid EPS data found for ticker {ticker}."
    return None  # No error message means success

@app.route("/", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def index():
    intrinsic_value = None
    error = None

    if request.method == "POST":
        ticker = request.form["ticker"].upper()
        error = get_eps_data(ticker)
        if error:
            return render_template("index.html", error=error)
        
        if not epsValues:
            error = f"No EPS data available for ticker {ticker}."
            return render_template("index.html", error=error)
        
        # Fetch stock price data using yfinance
        data = yf.download(ticker, start="2017-01-01", end="2023-12-31", interval="1d")
        if data.empty:
            error = f"No stock price data found for ticker {ticker}."
            return render_template("index.html", error=error)

        # Resample stock prices
        monthly_prices = data['Close'].resample('ME').last()
        yearly_avg_prices = monthly_prices.resample('YE').mean()

        # Extract prices and reverse the order
        price_array = [float(price) for price in yearly_avg_prices.squeeze().values]
        price_array.reverse()

        # Calculate P/E ratios
        peValues = [price_array[i] / epsValues[i] for i in range(len(epsValues))]

        # Remove outliers from the P/E ratios
        def remove_outliers_iqr(data, k=1.5):
            q1, q3 = np.percentile(data, [25, 75])
            iqr = q3 - q1
            lower_bound = q1 - k * iqr
            upper_bound = q3 + k * iqr
            return [x for x in data if lower_bound <= x <= upper_bound]

        newPe = remove_outliers_iqr(peValues)
        avgPE = sum(newPe) / len(newPe)

        # Calculate the intrinsic value
        intrinsic_value = avgPE * epsValues[0]
    
    return render_template("index.html", intrinsic_value=intrinsic_value, error=error)

if __name__ == "__main__":
    app.run(debug=True)
