import os
import json
import time
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from dotenv import load_dotenv
import alpaca_trade_api as tradeapi
from utils.backtest_engine import BacktestEngine
from utils.data_fetcher import DataFetcher
from utils.strategy_parser import StrategyParser
from utils.auth_utils import register_user, verify_user, login_user, logout_user
from utils.trade_manager import save_paper_trade, get_user_portfolio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key')

# Ensure directories exist
os.makedirs('data/saved_strategies', exist_ok=True)
os.makedirs('data', exist_ok=True)
os.chmod('data/saved_strategies', 0o755)  # Read/write/execute for owner, read/execute for others

# Initialize Alpaca API
ALPACA_API_KEY = os.getenv('APCA_API_KEY_ID')
ALPACA_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY')
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url='https://paper-api.alpaca.markets')

# Initialize services
data_fetcher = DataFetcher(api)
backtest_engine = BacktestEngine(data_fetcher)

# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_email' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        success, message = login_user(email, password)
        if success:
            return redirect(url_for('index'))
        else:
            flash(message, 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_email' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('username')
        success, message = register_user(email, password, username)
        if success:
            flash('Registration successful! Please check your email for verification.', 'success')
            return redirect(url_for('verify'))
        else:
            flash(message, 'danger')
    return render_template('register.html')

@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'user_email' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        code = request.form.get('code')
        success, message = verify_user(email, code)
        if success:
            flash('Email verified! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
    return render_template('verify.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- MAIN ROUTES ---
@app.route('/')
def index():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/portfolio')
def portfolio():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    email = session['user_email']
    portfolio_data = get_user_portfolio(email)
    if not portfolio_data:
        flash('Error loading portfolio.', 'danger')
        return redirect(url_for('index'))
    return render_template('portfolio.html', portfolio=portfolio_data)

@app.route('/tutorial')
def tutorial():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('tutorial.html')

# --- TUTORIAL API ROUTES ---
@app.route('/api/tutorial/content')
def tutorial_content():
    with open('tutorials/content.json', 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/api/tutorial/terms')
def tutorial_terms():
    with open('tutorials/terms.json', 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

# --- API ROUTES ---
@app.route('/api/markets', methods=['GET'])
def get_market_status():
    try:
        clock = api.get_clock()
        return jsonify({
            'is_open': clock.is_open,
            'next_open': clock.next_open.isoformat(),
            'next_close': clock.next_close.isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching market status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/symbols', methods=['GET'])
def get_available_symbols():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        assets = api.list_assets(status='active')
        symbols = [asset.symbol for asset in assets if asset.tradable and asset.asset_class == 'us_equity']
        
        # Calculate pagination
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # If requested page exceeds total pages, return last page
        if start_idx >= len(symbols):
            page = (len(symbols) + per_page - 1) // per_page
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
        paginated_symbols = symbols[start_idx:min(end_idx, len(symbols))]
        
        return jsonify({
            'symbols': paginated_symbols,
            'total': len(symbols),
            'page': page,
            'pages': (len(symbols) + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Error fetching symbols: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/search-symbols', methods=['GET'])
def search_symbols():
    query = request.args.get('query', '').upper()
    try:
        assets = api.list_assets(status='active')
        symbols = [
            {"symbol": asset.symbol, "name": asset.name}
            for asset in assets
            if asset.tradable and asset.asset_class == 'us_equity' and
            (query in asset.symbol or (asset.name and query in asset.name.upper()))
        ]
        
        # Implement pagination for search results
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        paginated_symbols = symbols[start_idx:min(end_idx, len(symbols))]
        
        return jsonify({
            'symbols': paginated_symbols,
            'total': len(symbols),
            'page': page,
            'pages': (len(symbols) + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Error searching symbols: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical-data', methods=['GET'])
def get_historical_data():
    symbol = request.args.get('symbol', 'AAPL')
    timeframe = request.args.get('timeframe', '1D')
    period = request.args.get('period', '1M')
    try:
        data = data_fetcher.get_historical_data(symbol, timeframe, period)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/account', methods=['GET'])
def get_account():
    try:
        account = api.get_account()
        return jsonify({
            'cash': float(account.cash),
            'equity': float(account.equity),
            'buying_power': float(account.buying_power),
            'portfolio_value': float(account.portfolio_value),
            'status': account.status
        })
    except Exception as e:
        logger.error(f"Error fetching account: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    try:
        positions = api.list_positions()
        formatted_positions = []
        for position in positions:
            formatted_positions.append({
                'symbol': position.symbol,
                'qty': position.qty,
                'avg_entry_price': position.avg_entry_price,
                'current_price': position.current_price,
                'market_value': position.market_value,
                'unrealized_pl': position.unrealized_pl,
                'unrealized_plpc': position.unrealized_plpc
            })
        return jsonify(formatted_positions)
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    if 'user_email' not in session:
        return jsonify({"error": "Please log in to run a backtest"}), 401
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type, JSON required"}), 400
        strategy_config = request.get_json()
        symbol = strategy_config.get('symbol', 'AAPL')
        start_date = strategy_config.get('startDate', '2024-01-01')
        end_date = strategy_config.get('endDate', '2025-04-19')
        initial_capital = float(strategy_config.get('capital', 10000))
        blocks = strategy_config.get('blocks')
        
        if isinstance(blocks, dict) and 'indicators' in blocks:
            strategy = blocks
        else:
            parser = StrategyParser(blocks)
            strategy = parser.parse_blocks()
            
        # Log the parsed strategy
        logger.info(f"Running backtest for {symbol} from {start_date} to {end_date}")
        
        # Make sure we have some entry/exit rules
        if (not strategy.get('entry_rules') or not strategy.get('exit_rules')) and len(strategy.get('indicators', [])) > 0:
            logger.warning("No entry or exit rules found, adding default rules")
            
            # Add default entry rules if none exist
            if not strategy.get('entry_rules'):
                strategy['entry_rules'] = []
                # Try to create a rule based on the first indicator
                for ind in strategy['indicators']:
                    if ind['type'] == 'SMA':
                        period = ind['parameters']['period']
                        strategy['entry_rules'] = [
                            {'indicator': f"SMA_{period}", 'operator': '>', 'value': 'close'}
                        ]
                        break
                    elif ind['type'] == 'RSI':
                        period = ind['parameters']['period']
                        strategy['entry_rules'] = [
                            {'indicator': f"RSI_{period}", 'operator': '>', 'value': '50'}
                        ]
                        break
                    elif ind['type'] == 'EMA':
                        period = ind['parameters']['period']
                        strategy['entry_rules'] = [
                            {'indicator': f"EMA_{period}", 'operator': '>', 'value': 'close'}
                        ]
                        break
            
            # Add default exit rules if none exist
            if not strategy.get('exit_rules') and strategy.get('entry_rules'):
                strategy['exit_rules'] = []
                # Mirror the entry rules with opposite conditions
                for rule in strategy['entry_rules']:
                    exit_rule = rule.copy()
                    if exit_rule['operator'] == '>':
                        exit_rule['operator'] = '<'
                    elif exit_rule['operator'] == '<':
                        exit_rule['operator'] = '>'
                    elif exit_rule['operator'] == '>=':
                        exit_rule['operator'] = '<='
                    elif exit_rule['operator'] == '<=':
                        exit_rule['operator'] = '>='
                    strategy['exit_rules'].append(exit_rule)
        
        results = backtest_engine.run_backtest(
            strategy=strategy,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        # Log the results summary
        logger.info(f"Backtest completed: {results['total_trades']} trades, {results['total_return']}% return")
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/paper-trade', methods=['POST'])
def submit_paper_trade():
    if 'user_email' not in session:
        return jsonify({'error': 'Please log in to paper trade'}), 401
    if not request.is_json:
        return jsonify({'error': 'Invalid request format'}), 400
    email = session['user_email']
    trade_data = request.json
    success, result = save_paper_trade(email, trade_data)
    if success:
        return jsonify({
            'success': True,
            'message': 'Trade executed successfully',
            'data': result
        })
    else:
        return jsonify({'error': result}), 400

@app.route('/api/portfolio/update', methods=['GET'])
def update_portfolio():
    if 'user_email' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    email = session['user_email']
    portfolio_data = get_user_portfolio(email)
    if not portfolio_data:
        return jsonify({'error': 'Failed to load portfolio'}), 400
    return jsonify({
        'success': True,
        'portfolio': portfolio_data
    })

@app.route('/api/save-strategy', methods=['POST'])
def save_strategy():
    if 'user_email' not in session:
        return jsonify({"error": "Please log in to save a strategy"}), 401
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid content type, JSON required"}), 400
        strategy_data = request.get_json()
        if 'blocks' not in strategy_data or not strategy_data['blocks']:
            return jsonify({"error": "Strategy blocks are required"}), 400
        
        strategy_data['user_email'] = session['user_email']
        strategy_data['username'] = session.get('username', 'Anonymous')
        strategy_name = strategy_data.get('name', f"strategy_{int(time.time())}")
        strategy_name = ''.join(c for c in strategy_name if c.isalnum() or c in '._- ')
        
        save_dir = 'data/saved_strategies'
        os.makedirs(save_dir, exist_ok=True)  # Ensure directory exists
        
        filepath = os.path.join(save_dir, f"{strategy_name}.json")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(strategy_data, f, indent=4)
        except PermissionError:
            return jsonify({"error": "Permission denied saving strategy"}), 403
        except IOError:
            return jsonify({"error": "IO error saving strategy"}), 500
            
        return jsonify({
            "success": True,
            "message": f"Strategy saved as {strategy_name}",
            "filename": f"{strategy_name}.json"
        })
    except Exception as e:
        logger.error(f"Error saving strategy: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/list-strategies', methods=['GET'])
def list_strategies():
    if 'user_email' not in session:
        return jsonify({"error": "Please log in to view strategies"}), 401
    try:
        user_email = session['user_email']
        strategy_files = os.listdir('data/saved_strategies')
        strategies = []
        
        for filename in strategy_files:
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join('data/saved_strategies', filename)
            try:
                with open(filepath, 'r') as f:
                    strategy_data = json.load(f)
                if 'user_email' not in strategy_data or strategy_data['user_email'] == user_email:
                    strategies.append(filename.replace('.json', ''))
            except:
                continue
                
        return jsonify({"strategies": strategies})
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/load-strategy', methods=['GET'])
def load_strategy():
    if 'user_email' not in session:
        return jsonify({"error": "Please log in to load a strategy"}), 401
    try:
        strategy_name = request.args.get('name')
        user_email = session['user_email']
        
        if not strategy_name:
            # Return a list of strategies instead
            return list_strategies()
            
        filepath = os.path.join('data/saved_strategies', f"{strategy_name}.json")
        if not os.path.exists(filepath):
            return jsonify({"error": f"Strategy '{strategy_name}' not found"}), 404
            
        try:
            with open(filepath, 'r') as f:
                strategy_data = json.load(f)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid strategy file format"}), 400
        except PermissionError:
            return jsonify({"error": "Permission denied accessing strategy file"}), 403
            
        if 'user_email' in strategy_data and strategy_data['user_email'] != user_email:
            return jsonify({"error": "You don't have permission to access this strategy"}), 403
            
        return jsonify(strategy_data)
    except Exception as e:
        logger.error(f"Error loading strategy: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
