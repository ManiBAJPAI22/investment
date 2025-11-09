"""
Real Market Data-Driven Dataset Generator.

Uses actual stock market streak and entropy analysis to generate
realistic order flow patterns for consensus testing.

Data source: investment/data/
    - streak_entropy_analysis.csv: Down streak patterns and entropy
    - streak_length_frequencies.csv: Streak distribution data
"""

import csv
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal


class RealMarketDataGenerator:
    """Generate trading datasets based on real stock market characteristics."""

    def __init__(self, data_dir: str = None):
        """
        Initialize with market data.

        Args:
            data_dir: Path to data directory (default: ../../../data/)
        """
        if data_dir is None:
            # Default to investment/data directory
            # From: investment/market_sim/tests/performance/ -> investment/data/
            current_dir = Path(__file__).parent
            data_dir = current_dir.parent.parent.parent / 'data'

        self.data_dir = Path(data_dir)
        self.stocks = self._load_stock_data()

        print(f"Loaded {len(self.stocks)} stocks from {self.data_dir}")

    def _load_stock_data(self) -> List[Dict[str, Any]]:
        """Load stock data from CSV files."""
        entropy_file = self.data_dir / 'streak_entropy_analysis.csv'

        if not entropy_file.exists():
            print(f"Warning: {entropy_file} not found")
            return []

        stocks = []
        with open(entropy_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stocks.append({
                    'ticker': row['ticker'],
                    'company_name': row['company_name'],
                    'max_down_streak': int(row['max_down_streak']),
                    'avg_down_streak': float(row['avg_down_streak']),
                    'total_down_streaks': int(row['total_down_streaks']),
                    'entropy': float(row['entropy'])
                })

        return stocks

    def get_stocks_by_entropy(self, min_entropy: float = None,
                             max_entropy: float = None) -> List[Dict]:
        """
        Filter stocks by entropy range.

        Args:
            min_entropy: Minimum entropy (default: no minimum)
            max_entropy: Maximum entropy (default: no maximum)

        Returns:
            List of stocks matching criteria
        """
        filtered = self.stocks

        if min_entropy is not None:
            filtered = [s for s in filtered if s['entropy'] >= min_entropy]

        if max_entropy is not None:
            filtered = [s for s in filtered if s['entropy'] <= max_entropy]

        return filtered

    def get_stocks_by_volatility(self, volatility_level: str) -> List[Dict]:
        """
        Get stocks by volatility category.

        Args:
            volatility_level: 'low', 'medium', 'high', 'extreme'

        Returns:
            List of stocks in that volatility category
        """
        if volatility_level == 'low':
            # Low entropy, small streaks
            return [s for s in self.stocks
                   if s['entropy'] < 0.8 and s['max_down_streak'] <= 6]

        elif volatility_level == 'medium':
            # Medium entropy, moderate streaks
            return [s for s in self.stocks
                   if 0.8 <= s['entropy'] < 1.5 and s['max_down_streak'] <= 9]

        elif volatility_level == 'high':
            # High entropy, large streaks
            return [s for s in self.stocks
                   if 1.5 <= s['entropy'] < 2.0 and s['max_down_streak'] <= 11]

        elif volatility_level == 'extreme':
            # Very high entropy, extreme streaks
            return [s for s in self.stocks
                   if s['entropy'] >= 2.0 or s['max_down_streak'] >= 12]

        else:
            raise ValueError(f"Unknown volatility level: {volatility_level}")

    def generate_realistic_orders(self, count: int,
                                  volatility_level: str = 'medium',
                                  base_price: float = 100.0) -> List[Dict[str, Any]]:
        """
        Generate orders based on real stock volatility characteristics.

        Args:
            count: Number of orders to generate
            volatility_level: 'low', 'medium', 'high', 'extreme'
            base_price: Starting price

        Returns:
            List of order dictionaries
        """
        stocks = self.get_stocks_by_volatility(volatility_level)

        if not stocks:
            raise ValueError(f"No stocks found for volatility level: {volatility_level}")

        # Pick a random stock from this volatility category
        stock = random.choice(stocks)
        symbol = stock['ticker']
        entropy = stock['entropy']
        max_streak = stock['max_down_streak']

        # Generate orders with characteristics matching this stock
        orders = []
        current_price = base_price

        # Price movement parameters based on entropy
        price_volatility = 0.001 * (1 + entropy)  # Higher entropy = more volatile
        trend_strength = 0.002 * max_streak / 10   # Streak length affects trends

        # Simulate streak-like behavior
        streak_direction = random.choice([1, -1])  # 1 = up, -1 = down
        streak_length = 0

        for i in range(count):
            # Simulate streaks based on stock's streak characteristics
            if streak_length >= max_streak or random.random() < 0.3:
                # End streak and possibly reverse
                streak_direction = random.choice([1, -1])
                streak_length = 0
            else:
                streak_length += 1

            # Price movement (combines trend + randomness)
            trend_move = streak_direction * trend_strength
            random_move = random.gauss(0, price_volatility)
            price_change = trend_move + random_move

            current_price = current_price * (1 + price_change)
            current_price = max(current_price, base_price * 0.5)  # Floor at 50% of base

            # Generate order
            side = random.choice(['buy', 'sell'])
            quantity = random.randint(1, 100)

            # Add price spread based on volatility
            spread = price_volatility * 2
            if side == 'buy':
                price = current_price * (1 - spread)
            else:
                price = current_price * (1 + spread)

            orders.append({
                'symbol': symbol,
                'side': side,
                'price': round(price, 2),
                'quantity': quantity,
                'timestamp': i,
                'metadata': {
                    'stock_entropy': entropy,
                    'max_down_streak': max_streak,
                    'volatility_level': volatility_level
                }
            })

        return orders

    def generate_multi_stock_orders(self, count: int,
                                    num_stocks: int = 5,
                                    mix_volatility: bool = True) -> List[Dict[str, Any]]:
        """
        Generate orders across multiple stocks with varying volatility.

        Args:
            count: Total number of orders
            num_stocks: Number of different stocks to trade
            mix_volatility: Mix different volatility levels

        Returns:
            List of order dictionaries
        """
        if mix_volatility:
            # Select stocks from each volatility category
            stocks = []
            levels = ['low', 'medium', 'high', 'extreme']
            stocks_per_level = max(1, num_stocks // len(levels))

            for level in levels:
                level_stocks = self.get_stocks_by_volatility(level)
                if level_stocks:
                    stocks.extend(random.sample(level_stocks,
                                              min(stocks_per_level, len(level_stocks))))

            stocks = stocks[:num_stocks]  # Trim to exact count

        else:
            # Random selection
            stocks = random.sample(self.stocks, min(num_stocks, len(self.stocks)))

        if not stocks:
            raise ValueError("No stocks available")

        # Generate orders distributed across stocks
        orders = []
        orders_per_stock = count // len(stocks)

        for stock in stocks:
            symbol = stock['ticker']
            entropy = stock['entropy']
            max_streak = stock['max_down_streak']

            # Determine volatility level
            if entropy < 0.8:
                vol_level = 'low'
            elif entropy < 1.5:
                vol_level = 'medium'
            elif entropy < 2.0:
                vol_level = 'high'
            else:
                vol_level = 'extreme'

            # Generate orders for this stock
            stock_orders = self.generate_realistic_orders(
                orders_per_stock,
                volatility_level=vol_level,
                base_price=random.uniform(50.0, 500.0)
            )

            orders.extend(stock_orders)

        # Fill remaining orders
        remaining = count - len(orders)
        if remaining > 0:
            extra_orders = self.generate_realistic_orders(
                remaining,
                volatility_level='medium'
            )
            orders.extend(extra_orders)

        # Shuffle to mix stocks
        random.shuffle(orders)

        return orders[:count]

    def generate_entropy_stress_test(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate stress test with extreme entropy (most unpredictable stocks).

        Args:
            count: Number of orders

        Returns:
            List of order dictionaries
        """
        if not self.stocks:
            raise ValueError("No stock data loaded")

        # Get top 10 highest entropy stocks
        extreme_stocks = sorted(self.stocks, key=lambda s: s['entropy'], reverse=True)[:10]

        orders = []
        orders_per_stock = count // len(extreme_stocks)

        for stock in extreme_stocks:
            stock_orders = self.generate_realistic_orders(
                orders_per_stock,
                volatility_level='extreme',
                base_price=random.uniform(50.0, 500.0)
            )
            orders.extend(stock_orders)

        random.shuffle(orders)
        return orders[:count]

    def generate_low_volatility_test(self, count: int) -> List[Dict[str, Any]]:
        """
        Generate test with most stable stocks (low entropy, small streaks).

        Args:
            count: Number of orders

        Returns:
            List of order dictionaries
        """
        if not self.stocks:
            raise ValueError("No stock data loaded")

        # Get 10 lowest entropy stocks
        stable_stocks = sorted(self.stocks, key=lambda s: s['entropy'])[:10]

        orders = []
        orders_per_stock = count // len(stable_stocks)

        for stock in stable_stocks:
            stock_orders = self.generate_realistic_orders(
                orders_per_stock,
                volatility_level='low',
                base_price=random.uniform(50.0, 500.0)
            )
            orders.extend(stock_orders)

        random.shuffle(orders)
        return orders[:count]

    def get_pattern_summary(self) -> Dict[str, Any]:
        """Get summary statistics of available stock data."""
        if not self.stocks:
            return {}

        entropies = [s['entropy'] for s in self.stocks]
        streaks = [s['max_down_streak'] for s in self.stocks]

        return {
            'total_stocks': len(self.stocks),
            'entropy': {
                'min': min(entropies),
                'max': max(entropies),
                'avg': sum(entropies) / len(entropies)
            },
            'max_down_streak': {
                'min': min(streaks),
                'max': max(streaks),
                'avg': sum(streaks) / len(streaks)
            },
            'volatility_distribution': {
                'low': len(self.get_stocks_by_volatility('low')),
                'medium': len(self.get_stocks_by_volatility('medium')),
                'high': len(self.get_stocks_by_volatility('high')),
                'extreme': len(self.get_stocks_by_volatility('extreme'))
            }
        }


def main():
    """Demo usage of real market data generator."""
    import json

    gen = RealMarketDataGenerator()

    # Print summary
    summary = gen.get_pattern_summary()
    print("\n" + "="*60)
    print("REAL MARKET DATA SUMMARY")
    print("="*60)
    print(json.dumps(summary, indent=2))

    # Generate sample datasets
    print("\n" + "="*60)
    print("SAMPLE DATASETS")
    print("="*60)

    patterns = {
        'low_volatility': gen.generate_low_volatility_test(100),
        'medium_volatility': gen.generate_realistic_orders(100, 'medium'),
        'high_volatility': gen.generate_realistic_orders(100, 'high'),
        'extreme_stress': gen.generate_entropy_stress_test(100),
        'multi_stock': gen.generate_multi_stock_orders(100, num_stocks=10)
    }

    for name, orders in patterns.items():
        symbols = set(o['symbol'] for o in orders)
        avg_entropy = sum(o['metadata']['stock_entropy'] for o in orders) / len(orders)

        print(f"\n{name}:")
        print(f"  Orders: {len(orders)}")
        print(f"  Symbols: {', '.join(sorted(symbols))}")
        print(f"  Avg Entropy: {avg_entropy:.3f}")
        print(f"  Sample order: {orders[0]}")


if __name__ == '__main__':
    main()
