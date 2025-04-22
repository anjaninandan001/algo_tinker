# 🧠 AlgoBlocks - Low-Code Algorithmic Trading Platform

**AlgoBlocks** is a user-friendly, low-code platform that democratizes access to algorithmic trading. Built for retail investors, hobbyists, and financial enthusiasts, it empowers users to design, backtest, and paper trade algorithmic strategies **without writing code**.

## 🚀 Features

- 📊 **Drag-and-Drop Strategy Builder**: Create trading strategies with blocks for indicators, rules, and logic.
- 🔍 **Backtesting Engine**: Evaluate strategy performance on historical data with detailed metrics.
- 💡 **Paper Trading Simulator**: Test strategies in real-time without financial risk.
- 🔐 **Authentication System**: Secure login, registration, email verification.
- 📈 **Performance Analytics**: View equity curves, win rate, drawdown, and other key metrics.
- 📚 **In-Built Tutorials**: Step-by-step guidance for beginners and intermediate users.

## 🧱 Architecture Overview


## ⚙️ Tech Stack

- **Frontend**: HTML5, CSS3, Bootstrap, JavaScript
- **Backend**: Python, Flask
- **Trading API**: [Alpaca API](https://alpaca.markets/)
- **Data Handling**: Pandas, JSON
- **Charting**: Chart.js, TradingView

## 📽️ Demo Video

> (https://drive.google.com/drive/folders/1ti18EqKTuWYT7Mi670IVgd5Mjuw79ez3?usp=drive_link)

## 📷 Screenshots

> ![WhatsApp Image 2025-04-21 at 20 52 46_ac007a19](https://github.com/user-attachments/assets/0df5d8ac-4645-4dd3-adf3-ab132f1eea2f)


## 💡 Getting Started

### Prerequisites

- Python 3.9+

### Setup Instructions

```bash
# Clone this repo
git clone https://github.com/yourusername/algoblocks.git
cd algoblocks

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your .env file with the following keys
APCA_API_KEY_ID=your_key
APCA_API_SECRET_KEY=your_secret
SECRET_KEY=any_flask_secret
SMTP_USER=your_email
SMTP_PASSWORD=your_email_password

# Run the app
python app.py
