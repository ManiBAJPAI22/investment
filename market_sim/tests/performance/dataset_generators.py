"""
Advanced Dataset Generators for Consensus Testing.

Generates various types of trading patterns to stress-test consensus mechanisms:
- Random trading patterns
- High-frequency bursts
- Market maker patterns
- Flash crash scenarios
- Gradual volume increase
- Coordinated trading attacks
"""

import random
from typing import List, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta


class DatasetGenerator:
    """Generate different types of trading datasets for testing."""

    @staticmethod
    def random_orders(count: int, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generate random orders with uniform distribution.

        Simulates: Normal market conditions
        """
        if symbols is None:
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']

        orders = []
        for i in range(count):
            symbol = random.choice(symbols)
            base_price = {'AAPL': 150, 'GOOGL': 2800, 'MSFT': 300,
                         'AMZN': 3200, 'TSLA': 800}.get(symbol, 100)

            order = {
                'id': f'order_{i}',
                'symbol': symbol,
                'side': random.choice(['buy', 'sell']),
                'quantity': str(random.randint(100, 10000)),
                'price': f'{base_price + random.randint(-50, 50)}.{random.randint(0, 99):02d}',
                'agent_id': f'trader_{random.randint(1, 100)}',
                'timestamp': datetime.utcnow().isoformat()
            }
            orders.append(order)

        return orders

    @staticmethod
    def hft_burst_pattern(count: int, burst_size: int = 50, burst_count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate high-frequency trading burst pattern.

        Simulates: HFT algorithms submitting rapid bursts
        Pattern: [burst of 50] [pause] [burst of 50] [pause] ...
        """
        orders = []
        order_id = 0

        for burst in range(burst_count):
            # Burst of orders
            for i in range(burst_size):
                order = {
                    'id': f'hft_order_{order_id}',
                    'symbol': 'AAPL',
                    'side': 'buy' if i % 2 == 0 else 'sell',
                    'quantity': str(random.randint(100, 500)),
                    'price': f'{150 + random.randint(-2, 2)}.{random.randint(0, 99):02d}',
                    'agent_id': f'hft_firm_{burst % 5}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'burst_id': burst
                }
                orders.append(order)
                order_id += 1

            # Fill remaining with low activity if needed
            if len(orders) < count:
                pause_orders = min(10, count - len(orders))
                for i in range(pause_orders):
                    order = {
                        'id': f'normal_order_{order_id}',
                        'symbol': random.choice(['GOOGL', 'MSFT']),
                        'side': random.choice(['buy', 'sell']),
                        'quantity': str(random.randint(500, 2000)),
                        'price': f'{300 + random.randint(-10, 10)}.00',
                        'agent_id': f'trader_{random.randint(1, 50)}',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    orders.append(order)
                    order_id += 1

        return orders[:count]

    @staticmethod
    def market_maker_pattern(count: int, spread: float = 0.50) -> List[Dict[str, Any]]:
        """
        Generate market maker order pattern.

        Simulates: Market makers providing liquidity
        Pattern: Alternating buy/sell orders maintaining spread
        """
        orders = []
        base_price = 150.00

        for i in range(count):
            is_buy = i % 2 == 0
            side = 'buy' if is_buy else 'sell'

            # Market maker places orders on both sides with spread
            price_offset = -spread/2 if is_buy else spread/2
            price = base_price + price_offset + (i % 10) * 0.10

            order = {
                'id': f'mm_order_{i}',
                'symbol': 'AAPL',
                'side': side,
                'quantity': str(1000),  # Consistent size
                'price': f'{price:.2f}',
                'agent_id': f'market_maker_{i % 3}',
                'timestamp': datetime.utcnow().isoformat(),
                'order_type': 'market_making'
            }
            orders.append(order)

        return orders

    @staticmethod
    def flash_crash_pattern(count: int, crash_point: float = 0.5) -> List[Dict[str, Any]]:
        """
        Generate flash crash scenario.

        Simulates: Sudden market crash with panic selling
        Pattern: Normal trading -> Sudden sell pressure -> Recovery
        """
        orders = []
        crash_start = int(count * crash_point)
        crash_duration = int(count * 0.1)  # 10% of orders during crash

        for i in range(count):
            if crash_start <= i < crash_start + crash_duration:
                # Flash crash: heavy selling
                order = {
                    'id': f'crash_order_{i}',
                    'symbol': 'AAPL',
                    'side': 'sell',  # All sells
                    'quantity': str(random.randint(5000, 20000)),  # Large quantities
                    'price': f'{150 - (i - crash_start) * 2}.00',  # Falling prices
                    'agent_id': f'panic_seller_{i % 20}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'event': 'flash_crash'
                }
            elif i < crash_start:
                # Pre-crash: normal trading
                order = {
                    'id': f'normal_order_{i}',
                    'symbol': 'AAPL',
                    'side': random.choice(['buy', 'sell']),
                    'quantity': str(random.randint(100, 1000)),
                    'price': f'{150 + random.randint(-5, 5)}.00',
                    'agent_id': f'trader_{random.randint(1, 50)}',
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # Post-crash: recovery buying
                order = {
                    'id': f'recovery_order_{i}',
                    'symbol': 'AAPL',
                    'side': random.choice(['buy', 'buy', 'sell']),  # More buys
                    'quantity': str(random.randint(1000, 5000)),
                    'price': f'{130 + (i - crash_start - crash_duration) * 0.5}.00',
                    'agent_id': f'buyer_{random.randint(1, 30)}',
                    'timestamp': datetime.utcnow().isoformat(),
                    'event': 'recovery'
                }

            orders.append(order)

        return orders

    @staticmethod
    def gradual_volume_increase(count: int) -> List[Dict[str, Any]]:
        """
        Generate gradually increasing volume pattern.

        Simulates: Market opening with volume ramp-up
        Pattern: Low volume -> High volume (linear increase)
        """
        orders = []

        for i in range(count):
            # Volume increases linearly
            volume_factor = (i / count) * 10 + 1
            quantity = int(100 * volume_factor)

            order = {
                'id': f'volume_order_{i}',
                'symbol': random.choice(['AAPL', 'GOOGL', 'MSFT']),
                'side': random.choice(['buy', 'sell']),
                'quantity': str(quantity),
                'price': f'{150 + random.randint(-10, 10)}.00',
                'agent_id': f'trader_{random.randint(1, int(volume_factor * 10))}',
                'timestamp': datetime.utcnow().isoformat(),
                'volume_factor': volume_factor
            }
            orders.append(order)

        return orders

    @staticmethod
    def coordinated_attack_pattern(count: int, attack_size: int = 100) -> List[Dict[str, Any]]:
        """
        Generate coordinated trading attack pattern.

        Simulates: Coordinated attempt to manipulate market
        Pattern: Multiple traders executing similar orders simultaneously
        """
        orders = []
        attack_points = [count // 4, count // 2, 3 * count // 4]

        for i in range(count):
            is_attack = any(abs(i - ap) < attack_size // 2 for ap in attack_points)

            if is_attack:
                # Coordinated orders
                order = {
                    'id': f'attack_order_{i}',
                    'symbol': 'AAPL',
                    'side': 'buy',  # All buying to drive price up
                    'quantity': str(5000),
                    'price': f'{155 + random.randint(0, 5)}.00',  # Slightly above market
                    'agent_id': f'attacker_{i % 10}',  # Same 10 attackers
                    'timestamp': datetime.utcnow().isoformat(),
                    'event': 'coordinated_attack'
                }
            else:
                # Normal trading
                order = {
                    'id': f'normal_order_{i}',
                    'symbol': random.choice(['AAPL', 'GOOGL', 'MSFT']),
                    'side': random.choice(['buy', 'sell']),
                    'quantity': str(random.randint(100, 1000)),
                    'price': f'{150 + random.randint(-10, 10)}.00',
                    'agent_id': f'trader_{random.randint(1, 100)}',
                    'timestamp': datetime.utcnow().isoformat()
                }

            orders.append(order)

        return orders

    @staticmethod
    def multi_symbol_balanced(count: int, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """
        Generate balanced trading across multiple symbols.

        Simulates: Diversified portfolio trading
        Pattern: Equal distribution across symbols
        """
        if symbols is None:
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'FB', 'NVDA', 'JPM', 'V', 'WMT']

        base_prices = {
            'AAPL': 150, 'GOOGL': 2800, 'MSFT': 300, 'AMZN': 3200, 'TSLA': 800,
            'FB': 330, 'NVDA': 220, 'JPM': 155, 'V': 230, 'WMT': 145
        }

        orders = []
        for i in range(count):
            symbol = symbols[i % len(symbols)]
            base_price = base_prices.get(symbol, 100)

            order = {
                'id': f'multi_order_{i}',
                'symbol': symbol,
                'side': random.choice(['buy', 'sell']),
                'quantity': str(random.randint(100, 2000)),
                'price': f'{base_price + random.randint(-10, 10)}.{random.randint(0, 99):02d}',
                'agent_id': f'portfolio_trader_{random.randint(1, 30)}',
                'timestamp': datetime.utcnow().isoformat()
            }
            orders.append(order)

        return orders

    @staticmethod
    def get_all_patterns(size: int, include_real_data: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all dataset patterns for comprehensive testing.

        Args:
            size: Number of orders per pattern
            include_real_data: Include real market data patterns (default: True)

        Returns:
            Dictionary mapping pattern name to order lists
        """
        patterns = {
            'random': DatasetGenerator.random_orders(size),
            'hft_burst': DatasetGenerator.hft_burst_pattern(size),
            'market_maker': DatasetGenerator.market_maker_pattern(size),
            'flash_crash': DatasetGenerator.flash_crash_pattern(size),
            'volume_increase': DatasetGenerator.gradual_volume_increase(size),
            'coordinated_attack': DatasetGenerator.coordinated_attack_pattern(size),
            'multi_symbol': DatasetGenerator.multi_symbol_balanced(size)
        }

        # Add real market data patterns if available
        if include_real_data:
            try:
                from .real_data_generator import RealMarketDataGenerator
                gen = RealMarketDataGenerator()

                # Add real market patterns
                patterns.update({
                    'real_low_volatility': gen.generate_low_volatility_test(size),
                    'real_medium_volatility': gen.generate_realistic_orders(size, 'medium'),
                    'real_high_volatility': gen.generate_realistic_orders(size, 'high'),
                    'real_extreme_stress': gen.generate_entropy_stress_test(size),
                    'real_multi_stock': gen.generate_multi_stock_orders(size, num_stocks=10)
                })

            except (ImportError, ValueError) as e:
                # Real data not available, skip
                print(f"Warning: Real market data not available - {e}")

        return patterns
