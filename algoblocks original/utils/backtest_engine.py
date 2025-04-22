import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Engine for backtesting trading strategies with Alpaca data"""
    
    def __init__(self, data_fetcher):
        """
        Initialize the backtest engine
        
        Args:
            data_fetcher: Instance of DataFetcher to get market data
        """
        self.data_fetcher = data_fetcher
    
    def run_backtest(self, strategy, symbol='AAPL', start_date=None, end_date=None, initial_capital=10000.0):
        """
        Run a backtest for the given strategy
        
        Args:
            strategy (dict): Strategy configuration with indicators and rules
            symbol (str): Trading symbol
            start_date (str): Start date for backtest (YYYY-MM-DD)
            end_date (str): End date for backtest (YYYY-MM-DD)
            initial_capital (float): Initial capital amount
            
        Returns:
            dict: Backtest results including metrics and trades
        """
        # Log the start of backtest
        logger.info(f"Starting backtest for {symbol} with {len(strategy['indicators'])} indicators")
        
        # Get historical data
        historical_data = self.data_fetcher.get_historical_data(
            symbol=symbol,
            timeframe='1D',  # Daily data for backtesting
            period='2Y'      # Get enough data for calculations
        )
        
        if not historical_data or len(historical_data) < 30:
            logger.warning(f"Insufficient historical data for {symbol}")
            return {
                'error': f"Insufficient historical data for {symbol}",
                'initial_capital': initial_capital,
                'final_equity': initial_capital,
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'trades': [],
                'equity_curve': [initial_capital]
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(historical_data)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        # Filter by date range if provided
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]
        
        # Check if we have enough data after filtering
        if len(df) < 20:
            logger.warning(f"Insufficient data after date filtering")
            return {
                'error': "Insufficient data after date filtering",
                'initial_capital': initial_capital,
                'final_equity': initial_capital,
                'total_return': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'trades': [],
                'equity_curve': [initial_capital]
            }
        
        # Apply indicators based on strategy
        df = self._apply_indicators(df, strategy['indicators'])
        
        # Log available indicators after calculation
        logger.info(f"Available columns after indicator calculation: {df.columns.tolist()}")
        
        # Initialize variables for simulation
        cash = initial_capital
        shares = 0
        trades = []
        equity_curve = [initial_capital]
        
        # Run simulation day by day
        for i in range(len(df)):
            if i < 20:  # Skip first few rows for indicator calculation
                continue
                
            date = df.index[i].strftime('%Y-%m-%d')
            price = df['close'].iloc[i]
            
            # Get yesterday's row for signal calculation (to avoid lookahead bias)
            yesterday_data = df.iloc[i-1]
            
            # Check for NaN values in the row
            if yesterday_data.isnull().any():
                continue
            
            # Check entry conditions when we have no position
            if shares == 0:
                # Check if entry conditions are met
                entry_signal = self._evaluate_conditions(yesterday_data, strategy['entry_rules'])
                
                if entry_signal:
                    # Calculate position size (simple approach: use all available cash)
                    shares_to_buy = int(cash / price)
                    cost = shares_to_buy * price
                    
                    if shares_to_buy > 0:
                        # Log the trade
                        logger.info(f"BUY signal triggered on {date}: {shares_to_buy} shares at ${price:.2f}")
                        
                        # Record the trade
                        trades.append({
                            'date': date,
                            'type': 'BUY',
                            'price': price,
                            'shares': shares_to_buy,
                            'value': cost
                        })
                        
                        # Update portfolio
                        cash -= cost
                        shares = shares_to_buy
            
            # Check exit conditions when we have a position
            elif shares > 0:
                # Check if exit conditions are met
                exit_signal = self._evaluate_conditions(yesterday_data, strategy['exit_rules'])
                
                if exit_signal:
                    # Calculate sale value
                    sale_value = shares * price
                    
                    # Log the trade
                    logger.info(f"SELL signal triggered on {date}: {shares} shares at ${price:.2f}")
                    
                    # Record the trade
                    trades.append({
                        'date': date,
                        'type': 'SELL',
                        'price': price,
                        'shares': shares,
                        'value': sale_value
                    })
                    
                    # Update portfolio
                    cash += sale_value
                    shares = 0
            
            # Update equity curve
            current_equity = cash + (shares * price)
            equity_curve.append(current_equity)
        
        # Calculate performance metrics
        initial_equity = equity_curve[0]
        final_equity = equity_curve[-1]
        total_return = ((final_equity / initial_equity) - 1) * 100
        
        # Calculate other metrics
        daily_returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = 0.0
        if len(daily_returns) > 0 and np.std(daily_returns) > 0:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
        
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # Log backtest summary
        logger.info(f"Backtest completed: {len(trades)} trades, {total_return:.2f}% return")
        
        # Prepare and return results
        return {
            'initial_capital': initial_capital,
            'final_equity': round(final_equity, 2),
            'total_return': round(total_return, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'total_trades': len(trades),
            'trades': trades,
            'equity_curve': [round(eq, 2) for eq in equity_curve]
        }
    
    def _apply_indicators(self, df, indicators):
        """
        Apply technical indicators to the DataFrame
        
        Args:
            df (DataFrame): Price data
            indicators (list): List of indicator configurations
            
        Returns:
            DataFrame: DataFrame with indicators added
        """
        for indicator in indicators:
            try:
                if indicator['type'] == 'SMA':
                    period = indicator['parameters']['period']
                    df[f'SMA_{period}'] = df['close'].rolling(window=period).mean()
                    logger.info(f"Calculated SMA_{period}")
                
                elif indicator['type'] == 'EMA':
                    period = indicator['parameters']['period']
                    df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
                    logger.info(f"Calculated EMA_{period}")
                
                elif indicator['type'] == 'RSI':
                    period = indicator['parameters']['period']
                    delta = df['close'].diff()
                    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
                    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
                    
                    # Avoid division by zero
                    loss = loss.replace(0, np.nan)
                    rs = gain / loss
                    rs = rs.fillna(0)
                    
                    df[f'RSI_{period}'] = 100 - (100 / (1 + rs))
                    logger.info(f"Calculated RSI_{period}")
                
                elif indicator['type'] == 'MACD':
                    fast_period = indicator['parameters']['fast_period']
                    slow_period = indicator['parameters']['slow_period']
                    signal_period = indicator['parameters']['signal_period']
                    
                    # Calculate MACD line
                    df[f'EMA_{fast_period}'] = df['close'].ewm(span=fast_period, adjust=False).mean()
                    df[f'EMA_{slow_period}'] = df['close'].ewm(span=slow_period, adjust=False).mean()
                    df['MACD'] = df[f'EMA_{fast_period}'] - df[f'EMA_{slow_period}']
                    
                    # Calculate signal line
                    df['MACD_Signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
                    
                    # Calculate histogram
                    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
                    
                    logger.info(f"Calculated MACD with parameters: fast={fast_period}, slow={slow_period}, signal={signal_period}")
            
            except Exception as e:
                logger.error(f"Error calculating indicator {indicator['type']}: {str(e)}")
        
        return df
    
    def _evaluate_conditions(self, row, conditions):
        """
        Evaluate if trading conditions are met
        
        Args:
            row (Series): DataFrame row with indicator values
            conditions (list): List of condition configurations
            
        Returns:
            bool: True if conditions are met, False otherwise
        """
        if not conditions:
            return False
        
        results = []
        
        for condition in conditions:
            indicator = condition['indicator']
            operator = condition['operator']
            value = condition['value']
            
            # If indicator isn't in the row, skip this condition
            if indicator not in row:
                logger.warning(f"Indicator '{indicator}' not found in data. Available: {row.index.tolist()}")
                continue
            
            # Get the indicator value
            indicator_value = row[indicator]
            
            # Handle None or NaN values
            if pd.isna(indicator_value):
                logger.warning(f"Indicator '{indicator}' has NaN value")
                continue
            
            # Process the value to compare against
            compare_value = None
            
            # If value is another column name, get its value
            if isinstance(value, str) and value in row:
                compare_value = row[value]
            else:
                # Handle special values
                if value == 'close':
                    compare_value = row['close']
                elif value == 'open':
                    compare_value = row['open']
                elif value == 'high':
                    compare_value = row['high']
                elif value == 'low':
                    compare_value = row['low']
                else:
                    # Try to convert to float
                    try:
                        compare_value = float(value)
                    except (ValueError, TypeError):
                        logger.warning(f"Could not convert value '{value}' to a number")
                        continue
            
            # Handle None or NaN values in the comparison value
            if pd.isna(compare_value):
                logger.warning(f"Comparison value '{value}' is NaN")
                continue
            
            # Apply operator
            try:
                if operator == '>':
                    results.append(indicator_value > compare_value)
                elif operator == '<':
                    results.append(indicator_value < compare_value)
                elif operator == '==':
                    results.append(indicator_value == compare_value)
                elif operator == '>=':
                    results.append(indicator_value >= compare_value)
                elif operator == '<=':
                    results.append(indicator_value <= compare_value)
                else:
                    logger.warning(f"Unsupported operator: {operator}")
            except Exception as e:
                logger.error(f"Error evaluating condition: {str(e)}")
                continue
        
        # If no conditions could be evaluated, return False
        if not results:
            return False
        
        # Return True if all conditions are met
        return all(results)
    
    def _calculate_max_drawdown(self, equity_curve):
        """
        Calculate maximum drawdown percentage
        
        Args:
            equity_curve (list): List of equity values over time
            
        Returns:
            float: Maximum drawdown percentage
        """
        # Convert to numpy array for easier calculations
        equity = np.array(equity_curve)
        
        # Calculate the running maximum
        running_max = np.maximum.accumulate(equity)
        
        # Calculate the drawdown at each point
        drawdowns = (running_max - equity) / running_max
        
        # Handle any NaN values (if running_max is 0)
        drawdowns = np.nan_to_num(drawdowns)
        
        # Calculate the maximum drawdown as a percentage
        max_drawdown = np.max(drawdowns) * 100
        
        return max_drawdown
