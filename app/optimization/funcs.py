from itertools import product
from gurobipy import GRB
import gurobipy as gp
import math

from app.models import StockLength, DemandLength

# Pattern generating function

def generate_initial_patterns_for_length(stock_length, demand_lengths):

    """
    This function returns all possible patterns of the demand lengths that can fit
    in a single stock length. The waste in every cutting pattern is also returned.
    """

    patterns = []

    for combo in product(*(range(stock_length // l + 1) for l in demand_lengths)):

        total = sum(combo[i] * demand_lengths[i] for i in range(len(demand_lengths)))
        if 0 < total <= stock_length:
            patterns.append((combo, stock_length - total))  # pattern, waste

    return patterns


# Main optimization function

def optimize_cutting():

    # Gather all available stock lengths
    stock_lengths = StockLength.objects.all()
    stock_lengths = [s.length for s in stock_lengths]

    # Gather required demand lengths
    demands = DemandLength.objects.all()
    demand_data = [(d.code, d.length, d.qty) for d in demands]
    codes, lengths, qtys = zip(*demand_data)    
    lengths = list(lengths)
    qtys = list(qtys)
    
    all_patterns = []
    pattern_info = [] # stores (stock_length_index, pattern_index)

    for s_idx, sl in enumerate(stock_lengths):
        patterns = generate_initial_patterns_for_length(sl, lengths)
        for p_idx, (pattern, waste) in enumerate(patterns):
            all_patterns.append((s_idx, pattern, waste))
            pattern_info.append((s_idx, p_idx))


    model = gp.Model("multi_stock_cutting")
    model.setParam('OutputFlag', 0)
    x = model.addVars(len(all_patterns), vtype=GRB.INTEGER, name="use_pattern")

    # Demand constraint
    for i in range(len(lengths)):
        model.addConstr(
            gp.quicksum(pattern[1][i] * x[p] for p, pattern in enumerate(all_patterns)) >= qtys[i]
        )

    # Objective: minimize number of rolls used (or total waste optionally)
    # model.setObjective(
    #     gp.quicksum(x[p] for p in range(len(all_patterns))),
    #     GRB.MINIMIZE
    # )

    # Objective to minimize waste
    model.setObjective(
        gp.quicksum(all_patterns[p][2] * x[p] for p in range(len(all_patterns))),
        GRB.MINIMIZE
    )

    model.optimize()

    results = []
    stock_summary = []
    total_waste = 0
    used_stock_count = {s_idx: 0 for s_idx in range(len(stock_lengths))}
    waste_by_stock = {s_idx: 0 for s_idx in range(len(stock_lengths))}

    for p in range(len(all_patterns)):
        if x[p].X > 0.5:
            s_idx, pattern, waste = all_patterns[p]
            count = int(x[p].X)
            used_stock_count[s_idx] += count
            waste_by_stock[s_idx] += float(waste) * count
            total_waste += float(waste) * count

            pattern_with_codes = {
                codes[i] +'-'+ str(lengths[i]): pattern[i] for i in range(len(pattern)) if pattern[i] > 0
            }

            results.append({
                'stock_length': int(stock_lengths[s_idx]),
                'pattern': pattern_with_codes,
                'count': count,
                'waste': float(waste),
            })

    for s_idx in range(len(stock_lengths)):
        stock_summary.append({
            'stock_length': int(stock_lengths[s_idx]),
            'used_count': int(used_stock_count[s_idx]),
            'waste': int(waste_by_stock[s_idx])
        })

    total_waste = float(total_waste)

    return results, stock_summary, total_waste