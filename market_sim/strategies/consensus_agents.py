"""
Trading Agents for Distributed Exchange

Implements various trading strategies that interact with the
consensus-backed distributed exchange.

Agent Types:
1. SimpleMarketMaker - Provides liquidity with bid-ask spreads
2. MomentumTrader - Follows price trends
3. ArbitrageAgent - Exploits price inefficiencies
4. NoiseTrader - Random trading for market activity

Author: Blockchain Consensus Implementation Team
Date: November 2025
"""

import random
from typing import List, Optional, Dict, Tuple
from decimal import Decimal
from datetime import datetime
from collections import deque

from core.models.base import Order, Trade, OrderSide
from blockchain.consensus.distributed_exchange import DistributedExchange


class TradingAgent:
    """Base class for all trading agents."""

    def __init__(self, agent_id: str, symbols: List[str]):
        """
        Initialize trading agent.

        Args:
            agent_id: Unique identifier for agent
            symbols: List of symbols to trade
        """
        self.agent_id = agent_id
        self.symbols = symbols
        self.active_orders: Dict[str, List[Order]] = {symbol: [] for symbol in symbols}
        self.trade_history: List[Trade] = []
        self.positions: Dict[str, Decimal] = {symbol: Decimal('0') for symbol in symbols}

    def on_tick(self, exchange: DistributedExchange) -> List[Order]:
        """
        Called each simulation tick.

        Args:
            exchange: Distributed exchange instance

        Returns:
            List of orders to submit
        """
        raise NotImplementedError

    def on_trade(self, trade: Trade) -> None:
        """Called when a trade is executed."""
        self.trade_history.append(trade)


class SimpleMarketMaker(TradingAgent):
    """
    Simple market making strategy.

    Continuously quotes bid and ask prices around mid-market,
    providing liquidity and earning the spread.
    """

    def __init__(self,
                 agent_id: str,
                 symbols: List[str],
                 spread_bps: Decimal = Decimal('20'),  # 20 basis points
                 order_size: Decimal = Decimal('100'),
                 max_position: Decimal = Decimal('1000')):
        """
        Initialize market maker.

        Args:
            agent_id: Unique identifier
            symbols: Symbols to make markets in
            spread_bps: Bid-ask spread in basis points (1 bp = 0.01%)
            order_size: Size of each quote
            max_position: Maximum position size per symbol
        """
        super().__init__(agent_id, symbols)
        self.spread_bps = spread_bps
        self.order_size = order_size
        self.max_position = max_position
        self.reference_prices: Dict[str, Decimal] = {}

    def on_tick(self, exchange: DistributedExchange) -> List[Order]:
        """Generate market making quotes."""
        if not exchange.is_leader():
            return []

        symbol = exchange.symbol
        orders = []

        # Get current market state
        bids, asks = exchange.get_order_book_snapshot(depth=1)

        # Determine mid-market price
        if bids and asks:
            mid_price = (bids[0][0] + asks[0][0]) / 2
        elif bids:
            mid_price = bids[0][0]
        elif asks:
            mid_price = asks[0][0]
        else:
            # No market yet, use reference price
            mid_price = self.reference_prices.get(symbol, Decimal('150.00'))

        self.reference_prices[symbol] = mid_price

        # Calculate bid and ask prices
        spread_fraction = self.spread_bps / Decimal('10000')
        half_spread = mid_price * spread_fraction / 2

        bid_price = (mid_price - half_spread).quantize(Decimal('0.01'))
        ask_price = (mid_price + half_spread).quantize(Decimal('0.01'))

        # Check position limits
        current_position = self.positions.get(symbol, Decimal('0'))

        # Submit buy order if not at max long position
        if current_position < self.max_position:
            buy_order = Order.create_limit_order(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=self.order_size,
                price=bid_price,
                agent_id=self.agent_id
            )
            orders.append(buy_order)

        # Submit sell order if not at max short position
        if current_position > -self.max_position:
            sell_order = Order.create_limit_order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=self.order_size,
                price=ask_price,
                agent_id=self.agent_id
            )
            orders.append(sell_order)

        return orders


class MomentumTrader(TradingAgent):
    """
    Momentum trading strategy.

    Buys when price is trending up, sells when trending down.
    Uses simple moving average crossover logic.
    """

    def __init__(self,
                 agent_id: str,
                 symbols: List[str],
                 lookback_window: int = 10,
                 trade_size: Decimal = Decimal('50')):
        """
        Initialize momentum trader.

        Args:
            agent_id: Unique identifier
            symbols: Symbols to trade
            lookback_window: Number of ticks for momentum calculation
            trade_size: Size of each trade
        """
        super().__init__(agent_id, symbols)
        self.lookback_window = lookback_window
        self.trade_size = trade_size
        self.price_history: Dict[str, deque] = {
            symbol: deque(maxlen=lookback_window) for symbol in symbols
        }
        self.last_signal: Dict[str, Optional[str]] = {symbol: None for symbol in symbols}

    def on_tick(self, exchange: DistributedExchange) -> List[Order]:
        """Generate momentum-based trades."""
        if not exchange.is_leader():
            return []

        symbol = exchange.symbol
        orders = []

        # Get market summary
        summary = exchange.get_market_summary()
        last_price = summary.get('last_price')

        if not last_price:
            # No price yet
            return []

        # Update price history
        self.price_history[symbol].append(last_price)

        # Need enough history for signal
        if len(self.price_history[symbol]) < self.lookback_window:
            return []

        # Calculate momentum signal
        prices = list(self.price_history[symbol])
        recent_avg = sum(prices[-3:]) / 3  # Last 3 prices
        older_avg = sum(prices[:3]) / 3    # First 3 prices

        # Generate signal
        signal = None
        if recent_avg > older_avg * Decimal('1.005'):  # 0.5% threshold
            signal = 'BUY'
        elif recent_avg < older_avg * Decimal('0.995'):
            signal = 'SELL'

        # Only trade on signal change
        if signal and signal != self.last_signal[symbol]:
            bids, asks = exchange.get_order_book_snapshot(depth=1)

            if signal == 'BUY' and asks:
                # Market buy at best ask
                buy_order = Order.create_limit_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=self.trade_size,
                    price=asks[0][0],  # Cross the spread
                    agent_id=self.agent_id
                )
                orders.append(buy_order)

            elif signal == 'SELL' and bids:
                # Market sell at best bid
                sell_order = Order.create_limit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=self.trade_size,
                    price=bids[0][0],  # Cross the spread
                    agent_id=self.agent_id
                )
                orders.append(sell_order)

            self.last_signal[symbol] = signal

        return orders


class NoiseTrader(TradingAgent):
    """
    Random noise trader.

    Generates random buy/sell orders to create market activity.
    Useful for testing and simulation realism.
    """

    def __init__(self,
                 agent_id: str,
                 symbols: List[str],
                 trade_probability: float = 0.1,
                 min_size: Decimal = Decimal('10'),
                 max_size: Decimal = Decimal('100'),
                 price_variance: Decimal = Decimal('0.02')):  # 2%
        """
        Initialize noise trader.

        Args:
            agent_id: Unique identifier
            symbols: Symbols to trade
            trade_probability: Probability of trading each tick (0-1)
            min_size: Minimum order size
            max_size: Maximum order size
            price_variance: Maximum price variance from mid-market
        """
        super().__init__(agent_id, symbols)
        self.trade_probability = trade_probability
        self.min_size = min_size
        self.max_size = max_size
        self.price_variance = price_variance

    def on_tick(self, exchange: DistributedExchange) -> List[Order]:
        """Generate random orders."""
        if not exchange.is_leader():
            return []

        # Random decision to trade
        if random.random() > self.trade_probability:
            return []

        symbol = exchange.symbol
        orders = []

        # Get market state
        bids, asks = exchange.get_order_book_snapshot(depth=1)

        if not bids or not asks:
            return []

        mid_price = (bids[0][0] + asks[0][0]) / 2

        # Random side
        side = random.choice([OrderSide.BUY, OrderSide.SELL])

        # Random size
        size = Decimal(str(random.randint(int(self.min_size), int(self.max_size))))

        # Random price around mid
        variance = 1 + Decimal(str(random.uniform(-float(self.price_variance),
                                                   float(self.price_variance))))
        price = (mid_price * variance).quantize(Decimal('0.01'))

        order = Order.create_limit_order(
            symbol=symbol,
            side=side,
            quantity=size,
            price=price,
            agent_id=self.agent_id
        )
        orders.append(order)

        return orders


class ArbitrageAgent(TradingAgent):
    """
    Arbitrage trader.

    Looks for price discrepancies and exploits them.
    In a single exchange, this primarily trades on wide spreads.
    """

    def __init__(self,
                 agent_id: str,
                 symbols: List[str],
                 min_spread_bps: Decimal = Decimal('50'),  # 50 bps minimum
                 trade_size: Decimal = Decimal('75')):
        """
        Initialize arbitrage agent.

        Args:
            agent_id: Unique identifier
            symbols: Symbols to trade
            min_spread_bps: Minimum spread to exploit (basis points)
            trade_size: Size of arbitrage trades
        """
        super().__init__(agent_id, symbols)
        self.min_spread_bps = min_spread_bps
        self.trade_size = trade_size

    def on_tick(self, exchange: DistributedExchange) -> List[Order]:
        """Look for arbitrage opportunities."""
        if not exchange.is_leader():
            return []

        symbol = exchange.symbol
        orders = []

        # Get market state
        bids, asks = exchange.get_order_book_snapshot(depth=1)

        if not bids or not asks:
            return []

        best_bid = bids[0][0]
        best_ask = asks[0][0]
        spread = best_ask - best_bid

        # Calculate spread in basis points
        mid_price = (best_bid + best_ask) / 2
        spread_bps = (spread / mid_price) * Decimal('10000')

        # If spread is wide enough, trade both sides
        if spread_bps >= self.min_spread_bps:
            # Buy at best bid (provide liquidity)
            buy_order = Order.create_limit_order(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=self.trade_size,
                price=best_bid + Decimal('0.01'),  # Penny improvement
                agent_id=self.agent_id
            )
            orders.append(buy_order)

            # Sell at best ask (provide liquidity)
            sell_order = Order.create_limit_order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=self.trade_size,
                price=best_ask - Decimal('0.01'),  # Penny improvement
                agent_id=self.agent_id
            )
            orders.append(sell_order)

        return orders


# Example usage
if __name__ == '__main__':
    print("Trading Agents Demonstration")
    print("=" * 80)

    # Create agents
    mm = SimpleMarketMaker('MM_001', ['AAPL'], spread_bps=Decimal('20'))
    mt = MomentumTrader('MT_001', ['AAPL'], lookback_window=10)
    nt = NoiseTrader('NOISE_001', ['AAPL'], trade_probability=0.3)
    arb = ArbitrageAgent('ARB_001', ['AAPL'], min_spread_bps=Decimal('50'))

    print("\n✓ Created 4 trading agents:")
    print(f"  1. Market Maker: {mm.agent_id}")
    print(f"  2. Momentum Trader: {mt.agent_id}")
    print(f"  3. Noise Trader: {nt.agent_id}")
    print(f"  4. Arbitrage Agent: {arb.agent_id}")

    print("\n" + "=" * 80)
    print("✓ Trading agents ready for distributed exchange!")
