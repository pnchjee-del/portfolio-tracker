# Project Plan: Investment Portfolio Tracker

## 1. Project Overview
A web-based financial application designed to track user investments across various asset classes, including stocks, mutual funds, and bullions. Users can securely log in, record buy and sell transactions, monitor current portfolio valuations, and generate PDF reports representing their holdings on any specific date.

## 2. Technology Stack
*   **Backend Framework:** Python with Flask
*   **Template Engine:** Jinja2 (Flask default)
*   **Database:** SQLite (development) / PostgreSQL (production) via Flask-SQLAlchemy
*   **Authentication:** Flask-Login and Werkzeug (password hashing)
*   **Forms & Validation:** Flask-WTF
*   **PDF Generation:** WeasyPrint or pdfkit
*   **Live Market Data (Future Integration):** yfinance (Stocks), custom APIs (Mutual Funds/Bullion)

## 3. Core Features
1.  **User Authentication:** Secure registration, login, and session management. Users can only access their own financial data.
2.  **Transaction Ledger:** A system to record "Buy" and "Sell" transactions, including asset name, transaction date, quantity, and purchase/sale price.
3.  **Dashboard:** A summary view calculating total units held, total invested amount, and current market value based on real-time or manually updated prices.
4.  **Time-Travel Reporting:** The ability to calculate the exact state and value of the portfolio on any historical date.
5.  **PDF Export:** Downloadable reports of the portfolio's status for a given date.

## 4. Database Schema (SQLAlchemy Models)

*   **User**
    *   `id` (PK)
    *   `username` (String, Unique)
    *   `password_hash` (String)

*   **Asset**
    *   `id` (PK)
    *   `symbol_or_name` (String)
    *   `asset_type` (Enum: Stock, Mutual Fund, Bullion)
    *   `current_price` (Float) - *Updated via API or manually*
    *   `last_updated` (DateTime)

*   **Transaction**
    *   `id` (PK)
    *   `user_id` (FK -> User.id)
    *   `asset_id` (FK -> Asset.id)
    *   `transaction_type` (Enum: BUY, SELL)
    *   `quantity` (Float)
    *   `price_per_unit` (Float)
    *   `transaction_date` (DateTime)

## 5. Application Structure

```text
portfolio_app/
├── app.py                 # App factory and configuration
├── extensions.py          # SQLAlchemy, LoginManager instances
├── models.py              # Database schemas (User, Asset, Transaction)
├── routes.py              # Endpoints (Auth, Dashboard, Buy/Sell, Export)
├── forms.py               # Flask-WTF form classes
├── static/                # CSS and JS (Design added later)
└── templates/             # Jinja2 Templates
    ├── base.html          
    ├── login.html         
    ├── register.html      
    ├── dashboard.html     
    ├── transaction.html   
    └── pdf_report.html    
```

## 6. Development Phases

### Phase 1: Foundation & Authentication
*   Set up the Flask environment and folder structure.
*   Configure the SQLite database and SQLAlchemy.
*   Implement the `User` model.
*   Build registration, login, and logout routes using Flask-Login.

### Phase 2: Core Asset & Transaction Engine
*   Implement `Asset` and `Transaction` models.
*   Create Flask-WTF forms for buying and selling assets.
*   Build the routes to handle form submissions and save transactions to the database.

### Phase 3: Dashboard & Valuation Logic
*   Write the logic to aggregate transactions (calculate total holdings per asset by subtracting sells from buys).
*   Create the dashboard template to display total investments, current value, and profit/loss.
*   Implement a manual "update current price" feature for assets to establish the baseline valuation logic.

### Phase 4: Reporting & PDF Generation
*   Develop the algorithm to calculate portfolio state on a *specific date* (filtering transactions occurring on or before the target date).
*   Create a clean, print-friendly HTML template (`pdf_report.html`).
*   Integrate WeasyPrint/pdfkit to convert the rendered template into a downloadable PDF file.

### Phase 5: Polish & External APIs (Future)
*   Apply CSS/Design to the default Jinja2 templates.
*   Integrate external APIs to automatically fetch current prices for stocks and mutual funds.