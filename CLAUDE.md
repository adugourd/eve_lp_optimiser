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

**Advanced options:**
```bash
python eve_lp_optimizer.py --lp 100000 --cargo 5000 \
    --max-days 7.0 \
    --min-liquidity 0.5 \
    --categories ammo_s ammo_m \
    --output my_multibuy.txt
```

Available categories: `ammo_s`, `ammo_m`, `ammo_l`, `drone_light`, `drone_medium`

## Architecture

### Core Data Flow

1. **Item Configuration** (`LP_STORE_ITEMS`): Static list of all LP store offerings with:
   - Faction item (output) and base item (input) type IDs
   - LP cost, ISK cost, units per purchase
   - Volume and category metadata

2. **Market Data Fetching** (`ESIClient`):
   - Queries EVE ESI API for real-time Jita market prices
   - Gets sell orders (what you pay for base items, what you compete with for faction items)
   - Calculates market depth and daily volume from order books and history
   - Sample data mode bypasses API calls using hardcoded prices

3. **Analysis** (`analyze_items`):
   - For each LP store item, fetches both base and faction market data
   - Calculates profitability: `profit = (faction_sell_price * units) - (base_buy_price * units) - lp_isk_cost`
   - Computes ISK/LP ratio: `profit / lp_cost`
   - Estimates market liquidity: `daily_volume / units_per_purchase`

4. **Optimization** (`optimize_purchases`):
   - Greedy algorithm: sorts items by ISK/LP (penalized for low liquidity)
   - Allocates LP and cargo to highest-value items first
   - Respects constraints: LP budget, cargo volume, market depth
   - Limits purchases to avoid flooding low-volume markets

5. **Output Generation**:
   - **Multi-buy file**: List of BASE items to purchase (e.g., "Nuclear S x445000")
   - **Report file**: Detailed breakdown of purchases, costs, revenue, and profit

### Key Classes

- `LPStoreItem`: LP store offering definition (static configuration)
- `MarketData`: Current market state (price, volume, depth)
- `ItemAnalysis`: Combined LP store + market data with profitability metrics
- `ESIClient`: EVE ESI API wrapper with rate limiting and error handling

### Important Business Logic

**Market depth checking** (line 247-252): Orders within 5% of lowest price are considered "available" to avoid being undercut.

**Liquidity penalty** (line 353-359): Items with slow turnover get penalized ISK/LP to prevent overinvestment in illiquid markets.

**Volume limiting** (line 376-381): Purchases capped at `daily_volume * max_days_to_sell` to ensure realistic sell timeframes.

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
