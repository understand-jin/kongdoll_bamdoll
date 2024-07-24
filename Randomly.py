import numpy as np
import time
import random
from itertools import permutations
from util import Bundle, solution_check, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, solution, max_attempts=10):
    bundles = []
    remaining_orders = orders[:]
    
    while remaining_orders and rider.available_number > 0:
        current_order = remaining_orders.pop(0)
        current_bundle = [current_order]
        current_volume = current_order.volume

        attempts = 0
        while attempts < max_attempts and remaining_orders:
            added_to_bundle = False
            next_order = random.choice(remaining_orders)
            if current_volume + next_order.volume > rider.capa:
                attempts += 1
                continue
            
            current_bundle_ids = [o.id for o in current_bundle]
            next_bundle_ids = [next_order.id]

            combined_shop_seq = current_bundle_ids + next_bundle_ids
            combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

            is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
            if is_feasible == 0:
                current_bundle.append(next_order)
                current_volume += next_order.volume
                remaining_orders.remove(next_order)
                added_to_bundle = True
            else:
                attempts += 1

            if not added_to_bundle:
                break
        shop_seq = [order.id for order in current_bundle]
        delivery_seq = shop_seq[:]
        delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
        best_dlv_seq = delivery_seq

        final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
        bundles.append(final_bundle)

        solution.append([rider.type, shop_seq, best_dlv_seq])

        rider.available_number -= 1

    #print(f"Remaining orders after assigning to rider {rider.type}: {[order.id for order in remaining_orders]}")
    return bundles, remaining_orders


def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)

    solution = []

    bike_riders = [r for r in all_riders if r.type == 'BIKE']
    car_riders = [r for r in all_riders if r.type == 'CAR']
    walk_riders = [r for r in all_riders if r.type == 'WALK']

    all_bundles = []
    remaining_orders = sorted_orders[:]

    all_riders_list = bike_riders + car_riders + walk_riders
    random.shuffle(all_riders_list)

    while remaining_orders and all_riders_list:
        rider = all_riders_list.pop(0)
        if rider.available_number > 0:
            bundles, remaining_orders = assign_orders_to_rider(rider, remaining_orders, dist_mat, K, all_orders, solution)
            for bundle in bundles:
                all_bundles.append(bundle)
                #print(f"Added bundle to solution: rider = {rider.type}, shop_seq = {bundle.shop_seq}, dlv_seq = {bundle.dlv_seq}")


    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution

