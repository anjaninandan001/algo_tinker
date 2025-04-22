import os
import json
import logging
from datetime import datetime
from flask import session

logger = logging.getLogger(__name__)
USER_DATA_FILE = 'data/users.json'

def load_users():
    """Load users from JSON file"""
    try:
        with open(USER_DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading users: {str(e)}")
        return {}

def save_users(users):
    """Save users to JSON file"""
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving users: {str(e)}")
        return False

def save_paper_trade(email, trade_data):
    """
    Save a paper trade for a user
    
    Args:
        email (str): User email
        trade_data (dict): Trade data
        
    Returns:
        tuple: (success, result)
    """
    try:
        users = load_users()
        
        if email not in users:
            return False, "User not found"
        
        # Extract trade details
        symbol = trade_data.get('symbol')
        quantity = int(trade_data.get('quantity', 0))
        side = trade_data.get('side', 'buy').lower()
        order_type = trade_data.get('orderType', 'market').lower()
        price = float(trade_data.get('price', 0)) if order_type == 'limit' else None
        notes = trade_data.get('notes', '')
        
        # Validate trade data
        if not symbol:
            return False, "Symbol is required"
        
        if quantity <= 0:
            return False, "Quantity must be positive"
        
        if side not in ['buy', 'sell']:
            return False, "Side must be 'buy' or 'sell'"
        
        if order_type not in ['market', 'limit']:
            return False, "Order type must be 'market' or 'limit'"
        
        if order_type == 'limit' and (price is None or price <= 0):
            return False, "Valid price is required for limit orders"
        
        # Get user portfolio
        portfolio = users[email]['portfolio']
        cash = portfolio.get('cash', 10000.0)
        
        # Process the trade
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create trade record
        trade = {
            'timestamp': timestamp,
            'symbol': symbol,
            'quantity': quantity,
            'side': side,
            'type': order_type,
            'price': price if price else 100.0,  # Mock price for demo
            'status': 'executed',
            'notes': notes
        }
        
        # Update portfolio cash (simplified)
        if side == 'buy':
            trade_value = quantity * trade['price']
            if cash < trade_value:
                return False, "Insufficient funds"
            portfolio['cash'] = cash - trade_value
        else:  # sell
            trade_value = quantity * trade['price']
            portfolio['cash'] = cash + trade_value
        
        # Add trade to history
        if 'trades' not in portfolio:
            portfolio['trades'] = []
        
        portfolio['trades'].append(trade)
        
        # Save updated user data
        success = save_users(users)
        if not success:
            return False, "Failed to save trade"
        
        return True, trade
        
    except Exception as e:
        logger.error(f"Error saving paper trade: {str(e)}")
        return False, str(e)

def get_user_portfolio(email):
    """
    Get a user's portfolio data
    
    Args:
        email (str): User email
        
    Returns:
        dict: Portfolio data
    """
    try:
        users = load_users()
        
        if email not in users:
            return None
        
        portfolio = users[email].get('portfolio', {})
        
        # Calculate portfolio statistics
        trades = portfolio.get('trades', [])
        
        # Base stats
        stats = {
            'total_trades': len(trades),
            'win_rate': 0.0,
            'profit_loss': 0.0,
            'active_positions': []
        }
        
        # Calculate profit/loss and track positions
        position_tracker = {}
        profitable_trades = 0
        
        for trade in trades:
            symbol = trade['symbol']
            side = trade['side']
            quantity = trade['quantity']
            price = trade['price']
            
            # Track positions
            if side == 'buy':
                if symbol not in position_tracker:
                    position_tracker[symbol] = {
                        'quantity': 0,
                        'avg_price': 0,
                        'total_cost': 0
                    }
                
                current = position_tracker[symbol]
                new_quantity = current['quantity'] + quantity
                total_cost = current['total_cost'] + (quantity * price)
                
                position_tracker[symbol] = {
                    'quantity': new_quantity,
                    'avg_price': total_cost / new_quantity if new_quantity > 0 else 0,
                    'total_cost': total_cost
                }
                
            elif side == 'sell':
                if symbol in position_tracker:
                    current = position_tracker[symbol]
                    
                    # Calculate P/L for this sale
                    if current['quantity'] > 0:
                        sell_value = quantity * price
                        avg_cost = quantity * current['avg_price']
                        trade_pl = sell_value - avg_cost
                        stats['profit_loss'] += trade_pl
                        
                        if trade_pl > 0:
                            profitable_trades += 1
                    
                    # Update position
                    new_quantity = current['quantity'] - quantity
                    if new_quantity <= 0:
                        position_tracker[symbol] = {
                            'quantity': 0,
                            'avg_price': 0,
                            'total_cost': 0
                        }
                    else:
                        # Proportionally reduce total cost
                        remaining_ratio = new_quantity / current['quantity']
                        position_tracker[symbol] = {
                            'quantity': new_quantity,
                            'avg_price': current['avg_price'],
                            'total_cost': current['total_cost'] * remaining_ratio
                        }
        
        # Calculate win rate
        if len(trades) > 0:
            stats['win_rate'] = (profitable_trades / len(trades)) * 100
        
        # Format active positions
        for symbol, position in position_tracker.items():
            if position['quantity'] > 0:
                stats['active_positions'].append({
                    'symbol': symbol,
                    'quantity': position['quantity'],
                    'avg_price': position['avg_price'],
                    'total_cost': position['total_cost']
                })
        
        return {
            'cash': portfolio.get('cash', 10000.0),
            'trades': trades,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"Error getting user portfolio: {str(e)}")
        return None
