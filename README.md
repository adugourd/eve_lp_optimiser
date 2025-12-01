# EVE Online LP Store Optimizer

A Python tool that optimizes Loyalty Point (LP) store purchases for EVE Online's **Tribal Liberation Force**, helping you maximize profit from faction warfare LP.

## Features

- **Real-time Market Data**: Fetches live prices from Jita using the EVE ESI API
- **Profit Optimization**: Calculates ISK/LP ratios for all LP store items
- **Liquidity Analysis**: Considers market depth and daily volume to avoid illiquid items
- **Multi-constraint Optimization**: Respects LP budget, cargo capacity, and market absorption limits
- **Multi-buy Output**: Generates EVE-formatted shopping lists for easy in-game purchasing
- **Detailed Reports**: Shows profitability breakdown, investment costs, and expected returns

## How It Works

The LP store allows players to exchange:
- **Loyalty Points (LP)** + **ISK** + **Base Items (T1 ammo/drones)** → **Faction Items**

This tool finds the most profitable items by:
1. Fetching current market prices for both base items (what you buy) and faction items (what you sell)
2. Calculating profit per LP spent: `(sell_price - buy_cost - isk_cost) / lp_cost`
3. Optimizing purchases using a greedy algorithm with liquidity constraints
4. Generating a shopping list of base items to purchase

## Installation

### Prerequisites
- Python 3.7 or higher
- Internet connection (for ESI API access)

### Install Dependencies

```bash
pip install requests
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python eve_lp_optimizer.py --lp <available_lp> --cargo <cargo_capacity_m3>
```

**Example:**
```bash
python eve_lp_optimizer.py --lp 1000000 --cargo 5000
```

### Sample Data Mode (Testing)

Use sample market data instead of live API calls:

```bash
python eve_lp_optimizer.py --lp 100000 --cargo 5000 --sample
```

### Advanced Options

```bash
python eve_lp_optimizer.py --lp 1000000 --cargo 5000 \
    --max-days 7.0 \
    --min-liquidity 0.5 \
    --categories ammo_s ammo_m \
    --output my_purchases.txt
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--lp` | Available LP to spend (required) | - |
| `--cargo` | Cargo capacity in m³ (required) | - |
| `--output` | Output filename for multi-buy list | `multibuy.txt` |
| `--max-days` | Maximum days to sell inventory | `7.0` |
| `--min-liquidity` | Minimum daily volume (purchases/day) | `0.5` |
| `--sample` | Use sample data instead of live API | `False` |
| `--categories` | Limit to specific categories | All categories |

### Available Categories

- `ammo_s` - Small projectile ammo
- `ammo_m` - Medium projectile ammo
- `ammo_l` - Large projectile ammo
- `drone_light` - Light combat drones
- `drone_medium` - Medium combat drones

## Output

The tool generates two files:

### 1. Multi-buy List (`multibuy.txt`)
A list of base items to purchase, formatted for EVE's multi-buy interface:
```
Nuclear S x445000
Titanium Sabot S x1370000
Proton M x150000
Proton S x15000
```

**How to use:**
1. Copy the contents
2. In EVE, open any market window
3. Click "Multi-buy" in the bottom left
4. Paste and buy!

### 2. Detailed Report (`multibuy_report.txt`)
Comprehensive analysis including:
- Individual item profitability
- Total investment required
- Expected revenue and profit
- LP and cargo utilization
- Effective ISK/LP ratio

**Example snippet:**
```
================================================================================
EVE Online LP Store Optimizer - Results
================================================================================
Faction Item                          Units      LP  Base Cost    Revenue   ISK/LP
--------------------------------------------------------------------------------
Republic Fleet Nuclear S            445,000 106,800      3.55M    352.53M    2,268
Republic Fleet Titanium Sabot S   1,370,000 328,800     26.03M      1.07B    2,169
--------------------------------------------------------------------------------

SUMMARY
Total LP Used:                 487,200 (48.9%)
Base Items Cost:                35.70M (buy from market)
LP Store ISK Cost:             487.20M
Total Investment:              522.90M
Expected Revenue:                1.58B
Expected Profit:                 1.05B
Effective ISK/LP:                2,161
```

## Workflow

1. **Run the optimizer** with your available LP and cargo space
2. **Review the report** to check profitability and investment required
3. **Purchase base items** using the multi-buy list
4. **Visit the LP store** in-game and make the recommended exchanges
5. **Sell faction items** on the market in Jita

## Technical Details

### Market Data
- All prices fetched from **Jita** (The Forge region)
- Uses **sell orders** (competition prices for faction items, purchase prices for base items)
- Considers orders within 5% of best price for volume calculations
- Daily volume averaged over last 30 days of market history

### Optimization Algorithm
- **Greedy approach**: sorts items by ISK/LP ratio
- **Liquidity penalty**: reduces value for slow-selling items
- **Constraints**: respects LP budget, cargo capacity, and market depth
- **Market depth limiting**: won't purchase more than the market can absorb in the specified timeframe

### ESI API
The tool uses EVE's official ESI (EVE Swagger Interface) API:
- Base URL: `https://esi.evetech.net/latest`
- Rate limiting: 0.1s delay between requests
- No authentication required for market data

## Limitations

- **Faction-specific**: Currently configured for Tribal Liberation Force only
- **Jita-only**: All prices based on Jita market
- **No transaction costs**: Doesn't account for broker fees or sales tax
- **Static configuration**: LP store items are hardcoded (EVE updates may require code updates)
- **Market volatility**: Prices can change between analysis and execution

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is released under the MIT License. See LICENSE file for details.

## Disclaimer

This is a third-party tool and is not affiliated with or endorsed by CCP Games. EVE Online and all related content are trademarks of CCP hf.

Use at your own risk. Always verify market prices and profitability in-game before making large investments.

## Support

For bugs or feature requests, please open an issue on GitHub.

## Acknowledgments

- CCP Games for EVE Online and the ESI API
- The EVE Online community for market data and LP store mechanics documentation
