#!/usr/bin/env python3
"""
EVE Online LP Store Optimizer for Tribal Liberation Force

Calculates optimal LP store purchases considering:
- Cost to BUY base items (T1 ammo/drones) from Jita
- Revenue from SELLING faction items in Jita
- Market depth (enough volume at quoted price)
- LP and cargo constraints

Output: Multi-buy text for BASE items you need to purchase

Usage:
    python eve_lp_optimizer.py --lp 100000 --cargo 5000
    python eve_lp_optimizer.py --lp 100000 --cargo 5000 --sample  # Use sample data
"""

import requests
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import typer


# =============================================================================
# CONFIGURATION
# =============================================================================

THE_FORGE_REGION_ID = 10000002
JITA_SYSTEM_ID = 30000142
ESI_BASE_URL = "https://esi.evetech.net/latest"
REQUEST_DELAY = 0.1

# Sample market data for testing (price_per_unit, daily_volume)
# Base items - what you BUY (sell order prices = what you pay)
SAMPLE_BASE_PRICES = {
    # Small T1 ammo
    185: (8, 50000000),    # EMP S
    183: (7, 40000000),    # Fusion S
    184: (8, 45000000),    # Phased Plasma S
    182: (7, 30000000),    # Titanium Sabot S
    179: (5, 20000000),    # Nuclear S
    180: (6, 25000000),    # Proton S
    178: (4, 15000000),    # Carbonized Lead S
    181: (6, 18000000),    # Depleted Uranium S
    # Medium T1 ammo
    193: (40, 20000000),   # EMP M
    191: (35, 18000000),   # Fusion M
    192: (38, 22000000),   # Phased Plasma M
    190: (32, 15000000),   # Titanium Sabot M
    187: (25, 10000000),   # Nuclear M
    188: (28, 12000000),   # Proton M
    186: (20, 8000000),    # Carbonized Lead M
    189: (30, 9000000),    # Depleted Uranium M
    # Large T1 ammo
    201: (100, 8000000),   # EMP L
    199: (90, 7000000),    # Fusion L
    200: (95, 9000000),    # Phased Plasma L
    198: (80, 6000000),    # Titanium Sabot L
    195: (60, 4000000),    # Nuclear L
    196: (70, 5000000),    # Proton L
    194: (50, 3000000),    # Carbonized Lead L
    197: (75, 3500000),    # Depleted Uranium L
    # Drones
    2486: (18000, 50000),   # Warrior I
    15510: (75000, 30000),  # Valkyrie I
}

# Faction items - what you SELL (sell order prices = competition)
SAMPLE_FACTION_PRICES = {
    # Small faction ammo
    21898: (568, 377000),   # Republic Fleet EMP S
    21906: (616, 320000),   # Republic Fleet Fusion S
    21924: (482, 404000),   # Republic Fleet Phased Plasma S
    21939: (780, 247000),   # Republic Fleet Titanium Sabot S
    21914: (792, 156000),   # Republic Fleet Nuclear S
    21931: (651, 284000),   # Republic Fleet Proton S
    28328: (399, 98000),    # Republic Fleet Carbonized Lead S
    28336: (491, 111000),   # Republic Fleet Depleted Uranium S
    # Medium faction ammo
    21896: (949, 164000),   # Republic Fleet EMP M
    21904: (920, 161000),   # Republic Fleet Fusion M
    21922: (867, 277000),   # Republic Fleet Phased Plasma M
    21937: (776, 256000),   # Republic Fleet Titanium Sabot M
    21912: (720, 74000),    # Republic Fleet Nuclear M
    21928: (969, 109000),   # Republic Fleet Proton M
    28326: (609, 116000),   # Republic Fleet Carbonized Lead M
    28334: (940, 38000),    # Republic Fleet Depleted Uranium M
    # Large faction ammo
    21894: (1233, 161000),  # Republic Fleet EMP L
    21902: (1194, 92000),   # Republic Fleet Fusion L
    21918: (1295, 74000),   # Republic Fleet Phased Plasma L
    21935: (1074, 129000),  # Republic Fleet Titanium Sabot L
    21910: (910, 120000),   # Republic Fleet Nuclear L
    21926: (1186, 87000),   # Republic Fleet Proton L
    28324: (668, 51000),    # Republic Fleet Carbonized Lead L
    28332: (1108, 45000),   # Republic Fleet Depleted Uranium L
    # Faction drones
    31888: (1182000, 150),  # Republic Fleet Warrior
    31890: (1715000, 120),  # Republic Fleet Valkyrie
}


@dataclass
class LPStoreItem:
    """Represents an item available in the LP store"""
    name: str
    faction_type_id: int
    base_type_id: int
    base_name: str
    lp_cost: int
    isk_cost: int
    units_per_purchase: int
    volume_per_unit: float
    category: str
    
    @property
    def volume_per_purchase(self) -> float:
        return self.volume_per_unit * self.units_per_purchase


# LP Store items: faction_type_id, base_type_id, base_name, lp, isk, units, volume, category
LP_STORE_ITEMS: List[LPStoreItem] = [
    # Small Projectile Ammo (5000 units per purchase, 0.0025 m³/unit)
    LPStoreItem("Republic Fleet EMP S", 21898, 185, "EMP S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Fusion S", 21906, 183, "Fusion S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Phased Plasma S", 21924, 184, "Phased Plasma S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Titanium Sabot S", 21939, 182, "Titanium Sabot S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Nuclear S", 21914, 179, "Nuclear S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Proton S", 21931, 180, "Proton S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Carbonized Lead S", 28328, 178, "Carbonized Lead S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    LPStoreItem("Republic Fleet Depleted Uranium S", 28336, 181, "Depleted Uranium S", 1200, 1200000, 5000, 0.0025, "ammo_s"),
    # Medium Projectile Ammo (5000 units, 0.0125 m³/unit)
    LPStoreItem("Republic Fleet EMP M", 21896, 193, "EMP M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Fusion M", 21904, 191, "Fusion M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Phased Plasma M", 21922, 192, "Phased Plasma M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Titanium Sabot M", 21937, 190, "Titanium Sabot M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Nuclear M", 21912, 187, "Nuclear M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Proton M", 21928, 188, "Proton M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Carbonized Lead M", 28326, 186, "Carbonized Lead M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    LPStoreItem("Republic Fleet Depleted Uranium M", 28334, 189, "Depleted Uranium M", 1600, 1600000, 5000, 0.0125, "ammo_m"),
    # Large Projectile Ammo (5000 units, 0.025 m³/unit)
    LPStoreItem("Republic Fleet EMP L", 21894, 201, "EMP L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Fusion L", 21902, 199, "Fusion L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Phased Plasma L", 21918, 200, "Phased Plasma L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Titanium Sabot L", 21935, 198, "Titanium Sabot L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Nuclear L", 21910, 195, "Nuclear L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Proton L", 21926, 196, "Proton L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Carbonized Lead L", 28324, 194, "Carbonized Lead L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    LPStoreItem("Republic Fleet Depleted Uranium L", 28332, 197, "Depleted Uranium L", 2400, 2400000, 5000, 0.025, "ammo_l"),
    # Combat Drones (5 units per purchase)
    LPStoreItem("Republic Fleet Warrior", 31888, 2486, "Warrior I", 3000, 3000000, 5, 5.0, "drone_light"),
    LPStoreItem("Republic Fleet Valkyrie", 31890, 15510, "Valkyrie I", 4000, 4000000, 5, 10.0, "drone_medium"),
]


@dataclass
class MarketData:
    """Market data for an item"""
    type_id: int
    price: float           # Sell order price (what you pay to buy / compete with to sell)
    daily_volume: float    # Average daily volume traded
    available_volume: int  # Volume available at or near the price


class ESIClient:
    """Client for EVE Online ESI API"""
    
    def __init__(self, use_sample: bool = False):
        self.use_sample = use_sample
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EVE LP Optimizer',
            'Accept': 'application/json',
        })
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        if self.use_sample:
            return None
        url = f"{ESI_BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"  Warning: API request failed: {e}")
            return None
    
    def get_sell_orders(self, region_id: int, type_id: int) -> List[Dict]:
        """Get sell orders sorted by price (lowest first)"""
        if self.use_sample:
            return []
        orders = []
        page = 1
        while True:
            data = self._request(
                f"/markets/{region_id}/orders/",
                params={'type_id': type_id, 'order_type': 'sell', 'page': page}
            )
            if not data:
                break
            orders.extend(data)
            if len(data) < 1000:
                break
            page += 1
        
        # Filter to Jita and sort by price
        jita_orders = [o for o in orders if o.get('system_id') == JITA_SYSTEM_ID]
        if not jita_orders:
            jita_orders = orders
        return sorted(jita_orders, key=lambda x: x['price'])
    
    def get_market_history(self, region_id: int, type_id: int) -> List[Dict]:
        if self.use_sample:
            return []
        data = self._request(
            f"/markets/{region_id}/history/",
            params={'type_id': type_id}
        )
        return data if data else []
    
    def get_market_data(self, type_id: int, is_base_item: bool = False) -> Optional[MarketData]:
        """
        Get market data for an item.
        For base items: we want sell prices (what we pay to buy)
        For faction items: we want sell prices (competition) and depth
        """
        if self.use_sample:
            sample_dict = SAMPLE_BASE_PRICES if is_base_item else SAMPLE_FACTION_PRICES
            if type_id in sample_dict:
                price, volume = sample_dict[type_id]
                return MarketData(
                    type_id=type_id,
                    price=price,
                    daily_volume=volume,
                    available_volume=int(volume * 10)  # Estimate
                )
            return None
        
        orders = self.get_sell_orders(THE_FORGE_REGION_ID, type_id)
        if not orders:
            return None
        
        # Get lowest price and volume at/near that price (within 5%)
        # This represents realistic available volume before getting undercut
        min_price = orders[0]['price']
        price_threshold = min_price * 1.05
        available_volume = sum(
            o['volume_remain'] for o in orders
            if o['price'] <= price_threshold
        )
        
        # Get daily volume from history
        history = self.get_market_history(THE_FORGE_REGION_ID, type_id)
        if history:
            recent = history[-30:] if len(history) >= 30 else history
            daily_volume = sum(h['volume'] for h in recent) / len(recent)
        else:
            daily_volume = 0
        
        return MarketData(
            type_id=type_id,
            price=min_price,
            daily_volume=daily_volume,
            available_volume=available_volume
        )


@dataclass
class ItemAnalysis:
    """Analysis of an LP store item including market data"""
    item: LPStoreItem
    base_market: MarketData
    faction_market: MarketData
    base_cost_per_purchase: float   # Cost to buy base items
    faction_revenue_per_purchase: float  # Revenue from selling faction items
    total_cost_per_purchase: float  # base + isk cost
    profit_per_purchase: float
    net_isk_per_lp: float
    daily_volume_purchases: float   # Market can absorb this many purchases/day
    lp_per_m3: float                # LP cost per m³ (cargo efficiency)


def analyze_items(items: List[LPStoreItem], esi: ESIClient) -> List[ItemAnalysis]:
    """
    Fetch market data and analyze profitability for all LP store items.

    For each item, fetches current Jita market prices for both the base item
    (T1 ammo/drone) and the faction item, then calculates profitability metrics.

    Args:
        items: List of LP store items to analyze
        esi: ESI API client (real or sample mode)

    Returns:
        List of ItemAnalysis objects for profitable items only.
        Unprofitable items or items with missing market data are excluded.
    """
    analyses = []
    
    print("Fetching market data from Jita...")
    for i, item in enumerate(items):
        print(f"  [{i+1}/{len(items)}] {item.name}...", end=" ", flush=True)
        
        # Get base item prices (what we pay to buy T1 items)
        base_market = esi.get_market_data(item.base_type_id, is_base_item=True)
        if base_market is None:
            print("No base item data")
            continue
        
        # Get faction item prices (what we sell for)
        faction_market = esi.get_market_data(item.faction_type_id, is_base_item=False)
        if faction_market is None or faction_market.price <= 0:
            print("No faction item data")
            continue
        
        # Calculate costs and revenue per LP store purchase
        base_cost = base_market.price * item.units_per_purchase
        faction_revenue = faction_market.price * item.units_per_purchase
        total_cost = base_cost + item.isk_cost
        profit = faction_revenue - total_cost
        
        if profit <= 0:
            print(f"Not profitable ({profit/item.lp_cost:.0f} ISK/LP)")
            continue
        
        net_isk_per_lp = profit / item.lp_cost
        daily_volume_purchases = faction_market.daily_volume / item.units_per_purchase
        lp_per_m3 = item.lp_cost / item.volume_per_purchase if item.volume_per_purchase > 0 else 0

        analysis = ItemAnalysis(
            item=item,
            base_market=base_market,
            faction_market=faction_market,
            base_cost_per_purchase=base_cost,
            faction_revenue_per_purchase=faction_revenue,
            total_cost_per_purchase=total_cost,
            profit_per_purchase=profit,
            net_isk_per_lp=net_isk_per_lp,
            daily_volume_purchases=daily_volume_purchases,
            lp_per_m3=lp_per_m3
        )
        analyses.append(analysis)
        
        print(f"{net_isk_per_lp:.0f} ISK/LP (base: {base_market.price:.1f}, faction: {faction_market.price:.1f})")
    
    return analyses


def optimize_purchases(
    analyses: List[ItemAnalysis],
    available_lp: int,
    cargo_capacity: float,
    min_liquidity: float = 0.3,
    max_days_to_sell: float = 14.0,
    diversify: bool = True,
    batch_size_days: float = 4.0,
    lp_density_weight: float = 0.7
) -> List[Tuple[ItemAnalysis, int]]:
    """
    Optimize LP store purchases with optional diversification to spread across items.

    Uses either a diversified round-robin allocation (default) or greedy allocation.
    Diversification helps avoid concentrating too much volume in single items,
    reducing time to liquidate and market risk.

    Args:
        analyses: List of analyzed LP store items with market data
        available_lp: Total LP points available to spend
        cargo_capacity: Maximum cargo volume in m³
        min_liquidity: Minimum daily volume in purchases/day (default: 0.3)
        max_days_to_sell: Maximum days to sell inventory (default: 14.0)
        diversify: Use diversified allocation instead of greedy (default: True)
        batch_size_days: Days worth of volume to allocate per round (default: 4.0)
        lp_density_weight: Weight for LP/m³ in scoring (0-1, default: 0.7)
                          0 = pure ISK/LP optimization, 1 = pure LP density optimization

    Returns:
        List of (ItemAnalysis, quantity) tuples where quantity is the number
        of LP store purchases to make for each item.
    """

    # Filter out items with insufficient market liquidity
    viable_items = [a for a in analyses if a.daily_volume_purchases >= min_liquidity]
    if not viable_items:
        print("Warning: No items meet liquidity requirements, using all items")
        viable_items = analyses.copy()

    # Calculate average LP density for normalization
    avg_lp_per_m3 = sum(a.lp_per_m3 for a in viable_items) / len(viable_items) if viable_items else 1.0

    # Hybrid sorting: balance ISK/LP profitability with LP density (cargo efficiency)
    def sort_key(a: ItemAnalysis) -> float:
        # Start with ISK/LP
        base_value = a.net_isk_per_lp

        # Apply liquidity penalty for slow sellers
        if a.daily_volume_purchases > 0:
            days_to_sell_one = 1 / a.daily_volume_purchases
            if days_to_sell_one > max_days_to_sell:
                base_value *= (max_days_to_sell / days_to_sell_one)

        # Apply LP density boost (favors items that pack more LP per m³)
        if lp_density_weight > 0 and avg_lp_per_m3 > 0:
            density_factor = (a.lp_per_m3 / avg_lp_per_m3) ** lp_density_weight
            base_value *= density_factor

        return base_value

    viable_items.sort(key=sort_key, reverse=True)

    if not diversify:
        # Original greedy algorithm - allocate everything to best items first
        return _greedy_allocation(viable_items, available_lp, cargo_capacity, max_days_to_sell)
    else:
        # Diversified round-robin allocation - spread across multiple items
        return _diversified_allocation(
            viable_items, available_lp, cargo_capacity,
            max_days_to_sell, batch_size_days
        )


def _greedy_allocation(
    viable_items: List[ItemAnalysis],
    available_lp: int,
    cargo_capacity: float,
    max_days_to_sell: float
) -> List[Tuple[ItemAnalysis, int]]:
    """Original greedy allocation - fills up on best items first."""
    purchases: List[Tuple[ItemAnalysis, int]] = []
    remaining_lp = available_lp
    remaining_cargo = cargo_capacity

    for analysis in viable_items:
        if remaining_lp <= 0 or remaining_cargo <= 0:
            break

        item = analysis.item
        # Calculate maximum purchases based on each constraint
        max_by_lp = remaining_lp // item.lp_cost
        max_by_cargo = int(remaining_cargo // item.volume_per_purchase)

        # Limit by market depth (don't try to sell more than market absorbs)
        if analysis.daily_volume_purchases > 0:
            max_by_volume = int(analysis.daily_volume_purchases * max_days_to_sell)
        else:
            max_by_volume = 1

        # Take minimum of all constraints (at least 1 if possible)
        quantity = min(max_by_lp, max_by_cargo, max(1, max_by_volume))

        if quantity > 0:
            purchases.append((analysis, quantity))
            remaining_lp -= quantity * item.lp_cost
            remaining_cargo -= quantity * item.volume_per_purchase

    return purchases


def _diversified_allocation(
    viable_items: List[ItemAnalysis],
    available_lp: int,
    cargo_capacity: float,
    max_days_to_sell: float,
    batch_size_days: float
) -> List[Tuple[ItemAnalysis, int]]:
    """
    Diversified round-robin allocation - spreads purchases across items.

    Allocates in batches (e.g., 2 days worth of volume per item per round)
    to avoid concentrating heavily on single items.
    """
    # Track allocations per item using list of (analysis, quantity) tuples
    allocations = [[analysis, 0] for analysis in viable_items]
    remaining_lp = available_lp
    remaining_cargo = cargo_capacity

    # Keep allocating in rounds until resources exhausted
    allocation_made = True
    while allocation_made and remaining_lp > 0 and remaining_cargo > 0:
        allocation_made = False

        # Try to allocate to each item in priority order
        for alloc_entry in allocations:
            if remaining_lp <= 0 or remaining_cargo <= 0:
                break

            analysis = alloc_entry[0]
            current_qty = alloc_entry[1]
            item = analysis.item

            # Calculate batch size: smaller of batch_size_days or remaining capacity
            if analysis.daily_volume_purchases > 0:
                # Allocate batch_size_days worth of volume at a time
                batch_purchases = max(1, int(analysis.daily_volume_purchases * batch_size_days))
                # But never exceed max_days_to_sell total for this item
                max_total = int(analysis.daily_volume_purchases * max_days_to_sell)
                remaining_for_item = max(0, max_total - current_qty)
                batch_purchases = min(batch_purchases, remaining_for_item)
            else:
                batch_purchases = 1
                remaining_for_item = 1 - current_qty

            if remaining_for_item <= 0:
                continue

            # Apply resource constraints
            max_by_lp = remaining_lp // item.lp_cost
            max_by_cargo = int(remaining_cargo // item.volume_per_purchase)

            # Allocate the minimum of all constraints
            quantity = min(batch_purchases, max_by_lp, max_by_cargo)

            if quantity > 0:
                alloc_entry[1] += quantity
                remaining_lp -= quantity * item.lp_cost
                remaining_cargo -= quantity * item.volume_per_purchase
                allocation_made = True

    # Convert to list of tuples, filtering out zero allocations
    purchases = [(analysis, qty) for analysis, qty in allocations if qty > 0]

    return purchases


def format_isk(value: float) -> str:
    """
    Format ISK values with appropriate suffixes (B, M, k).

    Args:
        value: ISK amount to format

    Returns:
        Formatted string (e.g., "1.50B", "250.00M", "5.0k")
    """
    if abs(value) >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f}B"
    elif abs(value) >= 1_000_000:
        return f"{value/1_000_000:.2f}M"
    elif abs(value) >= 1_000:
        return f"{value/1_000:.1f}k"
    else:
        return f"{value:.0f}"


def generate_multibuy(purchases: List[Tuple[ItemAnalysis, int]]) -> str:
    """
    Generate EVE Online multi-buy format text for BASE items to purchase.

    Creates a list of T1 items that can be pasted into EVE's multi-buy interface
    to quickly purchase all required base items from the market.

    Args:
        purchases: List of (ItemAnalysis, quantity) tuples

    Returns:
        Multi-line string with format: "Item Name xQuantity"
    """
    lines = []
    for analysis, quantity in purchases:
        total_units = quantity * analysis.item.units_per_purchase
        # Output BASE item name, not faction item!
        lines.append(f"{analysis.item.base_name} x{total_units}")
    return "\n".join(lines)


def generate_report(
    purchases: List[Tuple[ItemAnalysis, int]],
    available_lp: int,
    cargo_capacity: float
) -> str:
    """
    Generate a detailed profitability report for the optimized purchases.

    Creates a formatted text report showing:
    - Individual item details (units, LP cost, revenue, ISK/LP)
    - Summary statistics (total investment, revenue, profit)
    - Resource utilization (LP used, cargo used)

    Args:
        purchases: List of (ItemAnalysis, quantity) tuples
        available_lp: Total LP available
        cargo_capacity: Maximum cargo volume in m³

    Returns:
        Multi-line formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("EVE Online LP Store Optimizer - Results")
    lines.append("=" * 80)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Available LP: {available_lp:,}")
    lines.append(f"Cargo Capacity: {cargo_capacity:,.1f} m³")
    lines.append("")
    
    total_lp_used = 0
    total_base_cost = 0
    total_isk_cost = 0
    total_revenue = 0
    total_volume = 0
    
    lines.append("-" * 80)
    lines.append(f"{'Faction Item':<35} {'Units':>7} {'LP':>7} {'Base Cost':>10} {'Revenue':>10} {'ISK/LP':>8}")
    lines.append("-" * 80)
    
    for analysis, quantity in purchases:
        item = analysis.item
        total_units = quantity * item.units_per_purchase
        lp_used = quantity * item.lp_cost
        base_cost = quantity * analysis.base_cost_per_purchase
        isk_cost = quantity * item.isk_cost
        revenue = quantity * analysis.faction_revenue_per_purchase
        volume = quantity * item.volume_per_purchase
        
        total_lp_used += lp_used
        total_base_cost += base_cost
        total_isk_cost += isk_cost
        total_revenue += revenue
        total_volume += volume
        
        lines.append(f"{item.name:<35} {total_units:>7,} {lp_used:>7,} {format_isk(base_cost):>10} {format_isk(revenue):>10} {analysis.net_isk_per_lp:>8,.0f}")
    
    lines.append("-" * 80)
    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Total LP Used:         {total_lp_used:>15,} ({total_lp_used/available_lp*100:.1f}%)")
    lines.append(f"Remaining LP:          {available_lp - total_lp_used:>15,}")
    lines.append(f"Base Items Cost:       {format_isk(total_base_cost):>15} (buy from market)")
    lines.append(f"LP Store ISK Cost:     {format_isk(total_isk_cost):>15}")
    lines.append(f"Total Investment:      {format_isk(total_base_cost + total_isk_cost):>15}")
    lines.append(f"Expected Revenue:      {format_isk(total_revenue):>15}")
    lines.append(f"Expected Profit:       {format_isk(total_revenue - total_base_cost - total_isk_cost):>15}")
    if total_lp_used > 0:
        effective_isk_lp = (total_revenue - total_base_cost - total_isk_cost) / total_lp_used
        lines.append(f"Effective ISK/LP:      {effective_isk_lp:>15,.0f}")
    lines.append(f"Total Volume:          {total_volume:>15,.1f} m³ ({total_volume/cargo_capacity*100:.1f}%)")
    lines.append("")
    
    return "\n".join(lines)


app = typer.Typer()


@app.command()
def main(
    lp: int = typer.Option(..., help="Available LP"),
    cargo: float = typer.Option(..., help="Cargo capacity in m³"),
    output: str = typer.Option("multibuy.txt", help="Output filename"),
    max_days: float = typer.Option(14.0, "--max-days", help="Max days to sell inventory"),
    min_liquidity: float = typer.Option(0.3, "--min-liquidity", help="Min daily volume in purchases/day"),
    sample: bool = typer.Option(False, "--sample", help="Use sample data instead of live API"),
    categories: Optional[List[str]] = typer.Option(
        None,
        "--categories",
        help="Limit to specific categories (choices: ammo_s, ammo_m, ammo_l, drone_light, drone_medium)"
    ),
    no_diversify: bool = typer.Option(
        False,
        "--no-diversify",
        help="Use greedy allocation instead of diversified (concentrates on fewer items)"
    ),
    batch_days: float = typer.Option(
        4.0,
        "--batch-days",
        help="Days worth of volume to allocate per round when diversifying"
    ),
    lp_density: float = typer.Option(
        0.7,
        "--lp-density",
        help="Weight for LP/m³ optimization (0-1). Higher = favor denser items to use more LP per cargo"
    ),
):
    """
    EVE Online LP Store Optimizer for Tribal Liberation Force.

    Calculates optimal LP store purchases considering market prices,
    liquidity constraints, and cargo capacity.
    """
    # Validate categories if provided
    valid_categories = ["ammo_s", "ammo_m", "ammo_l", "drone_light", "drone_medium"]
    if categories:
        invalid = [c for c in categories if c not in valid_categories]
        if invalid:
            typer.echo(f"Error: Invalid categories: {', '.join(invalid)}")
            typer.echo(f"Valid choices: {', '.join(valid_categories)}")
            raise typer.Exit(1)

    print(f"\nEVE LP Store Optimizer (Tribal Liberation Force)")
    print(f"=" * 55)
    print(f"LP Available: {lp:,}")
    print(f"Cargo: {cargo:,.1f} m³")
    if sample:
        print("Mode: SAMPLE DATA (run without --sample for live prices)")
    print()

    items = LP_STORE_ITEMS
    if categories:
        items = [i for i in items if i.category in categories]
        print(f"Categories: {', '.join(categories)}")

    esi = ESIClient(use_sample=sample)
    analyses = analyze_items(items, esi)

    if not analyses:
        print("Error: No profitable items found")
        raise typer.Exit(1)

    print(f"\nOptimizing {len(analyses)} profitable items...")
    if not no_diversify:
        print(f"Using diversified allocation (batch size: {batch_days} days)")
    else:
        print("Using greedy allocation (may concentrate on fewer items)")

    purchases = optimize_purchases(
        analyses, lp, cargo,
        min_liquidity=min_liquidity,
        max_days_to_sell=max_days,
        diversify=not no_diversify,
        batch_size_days=batch_days,
        lp_density_weight=lp_density
    )

    if not purchases:
        print("Error: No viable purchases")
        raise typer.Exit(1)

    report = generate_report(purchases, lp, cargo)
    print()
    print(report)

    # Generate multi-buy for BASE items
    multibuy = generate_multibuy(purchases)

    with open(output, 'w') as f:
        f.write(multibuy)

    print(f"Multi-buy (BASE items to purchase) saved to: {output}")
    print("-" * 55)
    print(multibuy)
    print("-" * 55)

    report_file = output.rsplit('.', 1)[0] + "_report.txt"
    with open(report_file, 'w') as f:
        f.write(report)
        f.write("\n\nMULTI-BUY (Base items to buy from market):\n")
        f.write("-" * 55 + "\n")
        f.write(multibuy)

    print(f"Report saved to: {report_file}")


if __name__ == "__main__":
    app()
