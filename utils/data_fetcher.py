import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataFetcher:
    """Class for fetching market data from Alpaca"""
    
    def __init__(self, api):
        """Initialize with an Alpaca API client"""
        self.api = api
        self.cache = {}  # Simple cache for historical data
    
    def get_historical_data(self, symbol, timeframe='1D', period='1Y'):
        """
        Get historical price data for a symbol
        
        Args:
            symbol (str): Trading symbol (e.g., 'AAPL')
            timeframe (str): Timeframe for the data ('1D', '1H', '15Min', '5Min', '1Min')
            period (str): Time period to fetch ('1D', '1W', '1M', '3M', '6M', '1Y', '5Y')
            
        Returns:
            list: A list of dictionaries containing historical price data
        """
        # Generate cache key
        cache_key = f"{symbol}_{timeframe}_{period}"
        
        # Return cached data if available and not expired
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            # Cache for 1 hour
            if datetime.now() - cache_time < timedelta(hours=1):
                logger.info(f"Using cached data for {cache_key}")
                return data
        
        # Calculate start and end dates based on period
        end_date = datetime.now()
        
        if period == '1D':
            start_date = end_date - timedelta(days=1)
        elif period == '1W':
            start_date = end_date - timedelta(weeks=1)
        elif period == '1M':
            start_date = end_date - timedelta(days=30)
        elif period == '3M':
            start_date = end_date - timedelta(days=90)
        elif period == '6M':
            start_date = end_date - timedelta(days=180)
        elif period == '1Y':
            start_date = end_date - timedelta(days=365)
        elif period == '2Y':
            start_date = end_date - timedelta(days=365*2)
        else:  # '5Y'
            start_date = end_date - timedelta(days=365 * 5)
        
        # Format dates for API call
        start = start_date.strftime('%Y-%m-%d')
        end = end_date.strftime('%Y-%m-%d')
        
        # Map timeframe to Alpaca format
        timeframe_map = {
            '1Min': '1Min',
            '5Min': '5Min',
            '15Min': '15Min',
            '1H': '1Hour',
            '1D': '1Day'
        }
        alpaca_timeframe = timeframe_map.get(timeframe, '1Day')
        
        logger.info(f"Fetching {symbol} data from {start} to {end} with timeframe {alpaca_timeframe}")
        
        # Get data from Alpaca
        try:
            # Try using the newer bars API first
            try:
                bars = self.api.get_bars(
                    symbol=symbol,
                    timeframe=alpaca_timeframe,
                    start=start,
                    end=end,
                    limit=1000
                )
                
                data = []
                for bar in bars:
                    data.append({
                        'time': bar.t.strftime('%Y-%m-%d %H:%M:%S'),
                        'open': bar.o,
                        'high': bar.h,
                        'low': bar.l,
                        'close': bar.c,
                        'volume': bar.v
                    })
                
                # Cache the results
                self.cache[cache_key] = (datetime.now(), data)
                
                return data
                
            except AttributeError:
                # Fall back to older barset API
                bars = self.api.get_barset(
                    symbols=symbol,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                    limit=1000
                )
                
                # Convert to list of dictionaries
                if symbol in bars:
                    data = []
                    for bar in bars[symbol]:
                        data.append({
                            'time': bar.t.strftime('%Y-%m-%d %H:%M:%S'),
                            'open': bar.o,
                            'high': bar.h,
                            'low': bar.l,
                            'close': bar.c,
                            'volume': bar.v
                        })
                    
                    # Cache the results
                    self.cache[cache_key] = (datetime.now(), data)
                    
                    return data
        
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
        
        # Fall back to sample data if the API call fails
        logger.warning(f"Falling back to sample data for {symbol}")
        sample_data = self._get_sample_data(symbol)
        
        # Cache the sample data too
        self.cache[cache_key] = (datetime.now(), sample_data)
        
        return sample_data
    
    def get_real_time_quote(self, symbol):
        """
        Get real-time quote for a symbol
        
        Args:
            symbol (str): Trading symbol (e.g., 'AAPL')
            
        Returns:
            dict: Real-time quote data
        """
        try:
            # Try using the newer quotes API first
            try:
                quote = self.api.get_latest_quote(symbol)
                return {
                    'symbol': symbol,
                    'price': (quote.ap + quote.bp) / 2,  # Midpoint price
                    'ask': quote.ap,
                    'bid': quote.bp,
                    'timestamp': quote.t.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': quote.s
                }
            except AttributeError:
                # Fall back to bars for paper trading
                bars = self.api.get_barset(symbol, 'minute', limit=1)
                if symbol in bars and len(bars[symbol]) > 0:
                    bar = bars[symbol][0]
                    return {
                        'symbol': symbol,
                        'price': bar.c,
                        'timestamp': bar.t.strftime('%Y-%m-%d %H:%M:%S'),
                        'volume': bar.v
                    }
        except Exception as e:
            logger.error(f"Error fetching real-time quote for {symbol}: {str(e)}")
        
        # Return None if we couldn't get the data
        return None
    
    def _get_sample_data(self, symbol):
        """Generate sample data for testing when API is unavailable"""
        # Create a date range for the past year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        dates = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
        
        # Set a random seed based on the symbol for consistent results
        seed = sum(ord(c) for c in symbol)
        np.random.seed(seed)
        
        # Generate sample data with realistic price action
        base_price = 100.0 + (seed % 400)  # Different base price per symbol
        volatility = 0.01 + (seed % 100) * 0.0001  # Different volatility per symbol
        
        data = []
        current_price = base_price
        
        # Generate an uptrend, downtrend, or sideways pattern
        trend = np.random.choice(['up', 'down', 'sideways'])
        if trend == 'up':
            drift = 0.0005
        elif trend == 'down':
            drift = -0.0005
        else:
            drift = 0.0
        
        for date in dates:
            # Random daily volatility with drift
            price_change = np.random.normal(drift, volatility) * current_price
            current_price = max(current_price + price_change, 1.0)  # Ensure price doesn't go below 1
            
            # Daily high and low with realistic relationship to open/close
            if np.random.random() > 0.5:  # Bullish day
                open_price = current_price * (1 - np.random.random() * volatility)
                close_price = current_price
                high_price = close_price * (1 + np.random.random() * volatility)
                low_price = open_price * (1 - np.random.random() * volatility)
            else:  # Bearish day
                open_price = current_price * (1 + np.random.random() * volatility)
                close_price = current_price
                high_price = open_price * (1 + np.random.random() * volatility)
                low_price = close_price * (1 - np.random.random() * volatility)
            
            # Random volume
            volume = int(np.random.randint(100000, 10000000))
            
            data.append({
                'time': date.strftime('%Y-%m-%d'),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
        
        return data
