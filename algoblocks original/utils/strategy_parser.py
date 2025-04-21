import json
import logging

logger = logging.getLogger(__name__)

class StrategyParser:
    """Parser for block-based trading strategies"""
    
    def __init__(self, blocks):
        """
        Initialize with strategy blocks
        
        Args:
            blocks: List of block configurations or JSON string
        """
        logger.info("Initializing StrategyParser")
        
        # If blocks is a string, try to parse it as JSON
        if isinstance(blocks, str):
            try:
                self.blocks = json.loads(blocks)
                logger.info("Parsed blocks from JSON string")
            except json.JSONDecodeError:
                logger.error("Failed to parse blocks from JSON string")
                # Default to empty list if parsing fails
                self.blocks = []
        else:
            self.blocks = blocks
        
        # Initialize lists for storing parsed components
        self.indicators = []
        self.entry_rules = []
        self.exit_rules = []
    
    def parse_blocks(self):
        """
        Parse blocks into a strategy configuration
        
        Returns:
            dict: Strategy configuration with indicators and rules
        """
        logger.info(f"Parsing {len(self.blocks) if self.blocks else 0} blocks")
        
        # Process each block based on its type
        if self.blocks:
            for block in self.blocks:
                # Skip if block is not a dictionary (guard against incorrect input)
                if not isinstance(block, dict):
                    logger.warning(f"Skipping non-dict block: {block}")
                    continue
                
                block_type = block.get('type', '')
                logger.debug(f"Processing block of type: {block_type}")
                
                if block_type == 'indicator':
                    self._parse_indicator(block)
                elif block_type == 'entry':
                    self._parse_rule(block, is_entry=True)
                elif block_type == 'exit':
                    self._parse_rule(block, is_entry=False)
                else:
                    logger.warning(f"Unknown block type: {block_type}")
        
        # If no indicators were found, add a default SMA indicator
        if not self.indicators:
            logger.info("No indicators found, adding default SMA(20)")
            self.indicators.append({
                'type': 'SMA',
                'parameters': {
                    'period': 20,
                    'price': 'close'
                }
            })
        
        # If no entry rules were found, add a default entry rule
        if not self.entry_rules:
            logger.info("No entry rules found, adding default rule")
            indicator_name = "SMA_20"  # Default indicator
            
            # Find an indicator we can use for the default rule
            for ind in self.indicators:
                if ind['type'] == 'SMA':
                    period = ind['parameters']['period']
                    indicator_name = f"SMA_{period}"
                    break
                elif ind['type'] == 'RSI':
                    period = ind['parameters']['period']
                    indicator_name = f"RSI_{period}"
                    break
            
            # Add default entry rule based on the indicator
            if "RSI" in indicator_name:
                self.entry_rules.append({
                    'indicator': indicator_name,
                    'operator': '>',
                    'value': '50'
                })
            else:
                self.entry_rules.append({
                    'indicator': indicator_name,
                    'operator': '>',
                    'value': 'close'
                })
        
        # If no exit rules were found, add a default exit rule
        if not self.exit_rules:
            logger.info("No exit rules found, adding default rule")
            
            # Mirror the first entry rule with opposite condition
            if self.entry_rules:
                entry_rule = self.entry_rules[0]
                exit_rule = entry_rule.copy()
                
                # Flip the operator
                if exit_rule['operator'] == '>':
                    exit_rule['operator'] = '<'
                elif exit_rule['operator'] == '<':
                    exit_rule['operator'] = '>'
                elif exit_rule['operator'] == '>=':
                    exit_rule['operator'] = '<='
                elif exit_rule['operator'] == '<=':
                    exit_rule['operator'] = '>='
                
                self.exit_rules.append(exit_rule)
            else:
                # Fallback if somehow there are no entry rules
                self.exit_rules.append({
                    'indicator': 'SMA_20',
                    'operator': '<',
                    'value': 'close'
                })
        
        # Return the complete strategy configuration
        strategy = {
            'indicators': self.indicators,
            'entry_rules': self.entry_rules,
            'exit_rules': self.exit_rules
        }
        
        logger.info(f"Parsed strategy with {len(self.indicators)} indicators, {len(self.entry_rules)} entry rules, and {len(self.exit_rules)} exit rules")
        
        return strategy
    
    def _parse_indicator(self, block):
        """
        Parse an indicator block
        
        Args:
            block (dict): Block configuration
        """
        # Get indicator type, checking both formats that might be used
        indicator_type = block.get('indicatorType', '') or block.get('indicator_type', '')
        
        if not indicator_type:
            logger.warning("Block missing indicator type")
            return
        
        logger.debug(f"Parsing indicator: {indicator_type}")
        
        if indicator_type == 'SMA':
            period = int(block.get('period', 20))
            self.indicators.append({
                'type': 'SMA',
                'parameters': {
                    'period': period,
                    'price': 'close'
                }
            })
            logger.info(f"Added SMA indicator with period {period}")
        
        elif indicator_type == 'EMA':
            period = int(block.get('period', 20))
            self.indicators.append({
                'type': 'EMA',
                'parameters': {
                    'period': period,
                    'price': 'close'
                }
            })
            logger.info(f"Added EMA indicator with period {period}")
        
        elif indicator_type == 'RSI':
            period = int(block.get('period', 14))
            self.indicators.append({
                'type': 'RSI',
                'parameters': {
                    'period': period,
                    'price': 'close'
                }
            })
            logger.info(f"Added RSI indicator with period {period}")
        
        elif indicator_type == 'MACD':
            fast_period = int(block.get('fastPeriod', 12))
            slow_period = int(block.get('slowPeriod', 26))
            signal_period = int(block.get('signalPeriod', 9))
            
            self.indicators.append({
                'type': 'MACD',
                'parameters': {
                    'fast_period': fast_period,
                    'slow_period': slow_period,
                    'signal_period': signal_period,
                    'price': 'close'
                }
            })
            logger.info(f"Added MACD indicator with parameters: fast={fast_period}, slow={slow_period}, signal={signal_period}")
        
        else:
            logger.warning(f"Unsupported indicator type: {indicator_type}")
    
    def _parse_rule(self, block, is_entry=True):
        """
        Parse a rule block (entry or exit)
        
        Args:
            block (dict): Block configuration
            is_entry (bool): True if this is an entry rule, False for exit rule
        """
        rule_type = "entry" if is_entry else "exit"
        logger.debug(f"Parsing {rule_type} rule block")
        
        conditions = block.get('conditions', [])
        
        if not conditions:
            logger.warning(f"No conditions found in {rule_type} rule block")
            return
        
        for condition in conditions:
            if not isinstance(condition, dict):
                logger.warning(f"Skipping non-dict condition: {condition}")
                continue
            
            # Extract condition parameters
            indicator = condition.get('indicator', '')
            operator = condition.get('operator', '>')
            value = condition.get('value', 0)
            
            if not indicator:
                logger.warning(f"Missing indicator in condition")
                continue
            
            # Create rule object
            rule = {
                'indicator': indicator,
                'operator': operator,
                'value': value
            }
            
            # Add to appropriate rules list
            if is_entry:
                self.entry_rules.append(rule)
                logger.info(f"Added entry rule: {indicator} {operator} {value}")
            else:
                self.exit_rules.append(rule)
                logger.info(f"Added exit rule: {indicator} {operator} {value}")
