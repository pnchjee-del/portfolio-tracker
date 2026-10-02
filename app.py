import io
import os
import time
from datetime import datetime
import yfinance as yf
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, User, Asset, Transaction
from forms import LoginForm, RegistrationForm, TransactionForm


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-this-later')

database_url = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def generate_pdf(html_string):
    """
    Renders an HTML string into PDF bytes.
    Tries WeasyPrint first if system libraries (GTK/Pango) are installed.
    Falls back gracefully to xhtml2pdf for seamless cross-platform support.
    """
    import ctypes.util
    if ctypes.util.find_library('gobject-2.0-0') or ctypes.util.find_library('libgobject-2.0-0'):
        try:
            from weasyprint import HTML
            return HTML(string=html_string).write_pdf()
        except Exception:
            pass

    from xhtml2pdf import pisa
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=pdf_buffer)
    if pisa_status.err:
        raise RuntimeError("Failed to generate PDF report using xhtml2pdf.")
    return pdf_buffer.getvalue()

def get_user_portfolio(user_id):
    """
    Calculates current holdings and invested value for a user
    in chronological order using the average cost basis.
    """
    transactions = Transaction.query.filter_by(user_id=user_id)\
                                    .order_by(Transaction.transaction_date.asc(), Transaction.id.asc()).all()
    portfolio = {}
    for t in transactions:
        asset = t.asset or db.session.get(Asset, t.asset_id)
        if not asset:
            continue
            
        if asset.name not in portfolio:
            portfolio[asset.name] = {
                'type': asset.asset_type,
                'quantity': 0.0,
                'invested_value': 0.0
            }
        
        entry = portfolio[asset.name]
        if t.transaction_type == 'BUY':
            entry['quantity'] += t.quantity
            entry['invested_value'] += (t.quantity * t.price_per_unit)
        elif t.transaction_type == 'SELL':
            # Adjust invested value proportionally based on current average cost
            if entry['quantity'] > 0:
                avg_cost = entry['invested_value'] / entry['quantity']
                entry['invested_value'] -= (t.quantity * avg_cost)
            entry['quantity'] -= t.quantity
            
            # Avoid floating point negative residues
            if entry['quantity'] <= 0:
                entry['quantity'] = 0.0
                entry['invested_value'] = 0.0

    return {k: v for k, v in portfolio.items() if v['quantity'] > 0}

# Global in-memory cache for live ticker & market data
_market_cache = {
    'timestamp': 0,
    'data': None
}

TRACKED_STOCKS = [
    ('RELIANCE', 'RELIANCE', 1167.70, 1166.00),
    ('TCS', 'TCS', 2075.00, 2079.30),
    ('HDFCBANK', 'HDFC BANK', 721.20, 719.35),
    ('INFY', 'INFOSYS', 1035.00, 1035.00),
    ('ICICIBANK', 'ICICI BANK', 1310.60, 1305.50),
    ('SBIN', 'SBI', 954.10, 954.00),
    ('BHARTIARTL', 'AIRTEL', 1741.10, 1741.00),
    ('ITC', 'ITC', 255.90, 257.00),
    ('LT', 'L&T', 3693.40, 3685.50),
    ('HINDUNILVR', 'HIND UNILEVER', 1836.00, 1841.00),
    ('KOTAKBANK', 'KOTAK BANK', 418.35, 419.80),
    ('AXISBANK', 'AXIS BANK', 1217.10, 1214.00),
    ('BAJFINANCE', 'BAJAJ FINANCE', 948.30, 949.35),
    ('MARUTI', 'MARUTI SUZUKI', 11386.00, 11400.00),
    ('SUNPHARMA', 'SUN PHARMA', 1801.00, 1810.00),
    ('WIPRO', 'WIPRO', 159.35, 159.50),
    ('ASIANPAINT', 'ASIAN PAINTS', 2407.00, 2406.25),
    ('TITAN', 'TITAN', 4515.70, 4535.00)
]

def get_market_data():
    """
    Fetches and caches live benchmark indices and stock prices
    for both NSE and BSE exchanges covering 20+ liquid assets.
    """
    global _market_cache
    now = time.time()
    if _market_cache['data'] and (now - _market_cache['timestamp'] < 60):
        return _market_cache['data']

    symbols = ['^NSEI', '^NSEBANK', '^BSESN', 'BSE-100.BO']
    for sym_key, _, _, _ in TRACKED_STOCKS:
        symbols.append(f'{sym_key}.NS')
        symbols.append(f'{sym_key}.BO')

    try:
        df = yf.download(symbols, period='1d', interval='1d', progress=False)['Close']
        latest = df.iloc[-1]
    except Exception:
        latest = {}

    def val_of(sym, default=0.0):
        try:
            val = latest[sym]
            if hasattr(val, 'item'):
                val = val.item()
            if val is not None and not (isinstance(val, float) and (val != val)):
                return round(float(val), 2)
            return default
        except Exception:
            return default

    nse_tickers = [
        {'name': 'NIFTY 50', 'price': val_of('^NSEI', 22421.95), 'exchange': 'NSE'},
        {'name': 'BANK NIFTY', 'price': val_of('^NSEBANK', 54450.75), 'exchange': 'NSE'}
    ]
    nse_prices = {}

    bse_tickers = [
        {'name': 'SENSEX', 'price': val_of('^BSESN', 71909.70), 'exchange': 'BSE'},
        {'name': 'BSE 100', 'price': val_of('BSE-100.BO', 24029.64), 'exchange': 'BSE'}
    ]
    bse_prices = {}

    for sym_key, display_name, fallback_nse, fallback_bse in TRACKED_STOCKS:
        nse_p = val_of(f'{sym_key}.NS', fallback_nse)
        bse_p = val_of(f'{sym_key}.BO', fallback_bse)

        nse_tickers.append({'name': f'{display_name} (NSE)', 'price': nse_p, 'exchange': 'NSE'})
        nse_prices[sym_key] = nse_p

        bse_tickers.append({'name': f'{display_name} (BSE)', 'price': bse_p, 'exchange': 'BSE'})
        bse_prices[sym_key] = bse_p

    data = {
        'timestamp': now,
        'NSE': {
            'benchmark': nse_tickers[0],
            'secondary_index': nse_tickers[1],
            'tickers': nse_tickers,
            'prices': nse_prices
        },
        'BSE': {
            'benchmark': bse_tickers[0],
            'secondary_index': bse_tickers[1],
            'tickers': bse_tickers,
            'prices': bse_prices
        }
    }

    _market_cache['timestamp'] = now
    _market_cache['data'] = data
    return data

# --- ROUTES ---

@app.route('/')
@login_required
def dashboard():
    portfolio = get_user_portfolio(current_user.id)
    market_data = get_market_data()
    return render_template('dashboard.html', portfolio=portfolio, market_data=market_data)

@app.route('/download_report')
@login_required
def download_report():
    portfolio = get_user_portfolio(current_user.id)
    ledger_transactions = Transaction.query.filter_by(user_id=current_user.id)\
                                           .order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()

    rendered_html = render_template(
        'report.html', 
        portfolio=portfolio, 
        transactions=ledger_transactions,
        user=current_user,
        date=datetime.now().strftime("%d-%b-%Y")
    )

    try:
        pdf_bytes = generate_pdf(rendered_html)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Portfolio_Report_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        )
    except Exception as e:
        flash(f'Error generating PDF report: {e}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    
    if form.validate_on_submit():
        asset_name = form.asset_name.data.strip()
        asset_type = form.asset_type.data
        tx_type = form.transaction_type.data
        quantity = form.quantity.data
        price_per_unit = form.price_per_unit.data

        if quantity <= 0:
            flash('Quantity must be greater than zero.', 'danger')
            return render_template('add_transaction.html', form=form)

        if price_per_unit < 0:
            flash('Price per unit cannot be negative.', 'danger')
            return render_template('add_transaction.html', form=form)

        # Validate that the user owns sufficient units to sell
        if tx_type == 'SELL':
            current_portfolio = get_user_portfolio(current_user.id)
            current_qty = current_portfolio.get(asset_name, {}).get('quantity', 0.0)
            if current_qty < quantity:
                flash(f'Cannot sell {quantity} units of {asset_name}. You currently own {current_qty} units.', 'danger')
                return render_template('add_transaction.html', form=form)

        asset = Asset.query.filter_by(name=asset_name, asset_type=asset_type).first()
        if not asset:
            asset = Asset(name=asset_name, asset_type=asset_type)
            db.session.add(asset)
            db.session.commit()
        
        tx_datetime = datetime.combine(form.transaction_date.data, datetime.min.time())
        transaction = Transaction(
            user_id=current_user.id,
            asset_id=asset.id,
            transaction_type=tx_type,
            quantity=quantity,
            price_per_unit=price_per_unit,
            transaction_date=tx_datetime
        )
        db.session.add(transaction)
        db.session.commit()
        
        flash(f'Successfully logged {tx_type} for {asset.name}', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('add_transaction.html', form=form)

@app.route('/ledger')
@login_required
def ledger():
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
                                    .order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()
    return render_template('ledger.html', transactions=transactions)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data.strip()).first()
        if existing_user:
            flash('Username is already taken. Please choose a different one.', 'danger')
            return render_template('register.html', form=form)
            
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data.strip(), password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip()).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            flash('Login Unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/ticker')
def get_ticker_data():
    exchange = request.args.get('exchange', 'ALL').upper()
    market = get_market_data()
    
    if exchange == 'NSE':
        return jsonify(market['NSE']['tickers'])
    elif exchange == 'BSE':
        return jsonify(market['BSE']['tickers'])
    else:
        combined = [
            market['NSE']['benchmark'],
            market['BSE']['benchmark']
        ] + market['NSE']['tickers'][1:]
        return jsonify(combined)

@app.route('/api/market_data')
def api_market_data():
    return jsonify(get_market_data())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)