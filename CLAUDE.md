# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

EVE Online LP (Loyalty Point) Store Optimizer for Tribal Liberation Force. Calculates optimal LP store purchases considering:
- Cost to buy T1 base items (ammo/drones) from Jita market
- Revenue from selling faction items in Jita
- Market depth and liquidity constraints
- LP and cargo capacity limits

The optimizer outputs a multi-buy list of base items to purchase and a detailed profitability report.

## Running the Optimizer

**Basic usage:**
```bash
python eve_lp_optimizer.py --lp <available_lp> --cargo <cargo_capacity_m3>
```

**With sample data (for testing without API calls):**
```bash
python eve_lp_optimizer.py --lp 100000 --cargo 5000 --sample
```

**Quick liquidation mode (instant sell to buy orders):**
```bash
python eve_lp_optimizer.py --lp 100000 --cargo 5000 --liquidate
```

**Advanced options:**
```bash
python eve_lp_optimizer.py --lp 100000 --cargo 5000 \
    --max-days 7.0 \
    --min-liquidity 0.5 \
    --categories ammo_s ammo_m \
    --output my_multibuy.txt
```

Available categories: `ammo_s`, `ammo_m`, `ammo_l`, `drone_light`, `drone_medium`

## Liquidation Mode

The `--liquidate` flag enables quick liquidation mode, which:
- Uses **buy order prices** instead of sell order prices for faction items
- Provides **instant ISK** by selling directly to existing buy orders
- Typically yields **10-15% lower profit** than normal mode due to bid-ask spread
- Includes **automatic depth validation** to ensure buy orders can absorb recommended volumes

**Depth Validation**: When liquidation mode is enabled, the optimizer checks that selling 2X the recommended volume wouldn't cause the average buy price to drop by more than 5%. If it would, the quantity is automatically reduced to stay within safe depth. This prevents situations where buy orders collapse during the 30-minute round-trip to complete trades.

## Architecture

### Core Data Flow

1. **Item Configuration** (`LP_STORE_ITEMS`): Static list of all LP store offerings with:
   - Faction item (output) and base item (input) type IDs
   - LP cost, ISK cost, units per purchase
   - Volume and category metadata

2. **Market Data Fetching** (`ESIClient`):
   - Queries EVE ESI API for real-time Jita market prices
   - Gets sell orders (what you pay for base items) or buy orders (liquidation mode)
   - Stores full order books for accurate depth analysis
   - Calculates market depth and daily volume from order books and history
   - Sample data mode bypasses API calls using hardcoded prices

3. **Analysis** (`analyze_items`):
   - For each LP store item, fetches both base and faction market data
   - In normal mode: uses sell order prices (compete with other sellers)
   - In liquidation mode: uses buy order prices (instant sell to buyers)
   - Calculates profitability: `profit = (faction_price * units) - (base_cost * units) - lp_isk_cost`
   - Computes ISK/LP ratio: `profit / lp_cost`
   - Estimates market liquidity: `daily_volume / units_per_purchase`

4. **Optimization** (`optimize_purchases`):
   - Greedy or diversified algorithm: sorts items by ISK/LP (penalized for low liquidity)
   - Allocates LP and cargo to highest-value items first
   - Respects constraints: LP budget, cargo volume, market depth
   - Limits purchases to avoid flooding low-volume markets

5. **Depth Validation** (`validate_liquidation_depth`, liquidation mode only):
   - Checks that buy orders can absorb 2X the recommended volume
   - If average price drops >5%, reduces quantity to safe level
   - Uses binary search to find maximum safe quantity
   - Warns user about adjusted items

6. **Output Generation**:
   - **Multi-buy file**: List of BASE items to purchase (e.g., "Nuclear S x445000")
   - **Report file**: Detailed breakdown of purchases, costs, revenue, and profit

### Key Classes

- `LPStoreItem`: LP store offering definition (static configuration)
- `MarketData`: Current market state (price, volume, depth)
- `ItemAnalysis`: Combined LP store + market data with profitability metrics
- `ESIClient`: EVE ESI API wrapper with rate limiting and error handling

### Important Business Logic

**Market depth checking**: Orders within 5% of best price are considered "available" to avoid being undercut (sell orders) or price drops (buy orders).

**Order book walking** (`calculate_purchase_cost`, `calculate_sell_revenue`): Accurately calculates costs/revenue by walking through the order book depth rather than assuming a single price point.

**Liquidity penalty**: Items with slow turnover get penalized ISK/LP to prevent overinvestment in illiquid markets.

**Volume limiting**: Purchases capped at `daily_volume * max_days_to_sell` to ensure realistic sell timeframes.

**Depth validation** (`validate_liquidation_depth`): In liquidation mode, verifies that selling 2X the recommended volume won't cause >5% price drop. Uses binary search to find safe quantities.

## Dependencies

- `requests`: HTTP client for ESI API
- Standard library: `dataclasses`, `typing`, `datetime`, `argparse`, `time`

No external package manager files. Install dependencies via:
```bash
pip install requests
```

## File Structure

- `eve_lp_optimizer.py`: Main optimizer script (current version)
- `eve_lp_optimizer_old.py`: Previous version (reference/backup)
- `multibuy.txt`: Generated multi-buy output (BASE items to purchase)
- `multibuy_report.txt`: Detailed profitability report

## EVE Online Context

**LP Store Mechanics**: Players earn LP from faction warfare missions, then exchange LP + ISK + base items for faction items.

**Market arbitrage**: Profit comes from buying cheap T1 ammo/drones, converting via LP store, selling faction items at markup.

**Jita market**: Main trade hub (system_id: 30000142, region: The Forge 10000002). All prices reference Jita sell orders.

**Type IDs**: EVE's item identifier system (e.g., 185 = EMP S, 21898 = Republic Fleet EMP S).
