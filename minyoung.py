import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
import concurrent.futures

def find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, num_orders=30):
    bundle_size = len(current_bundle)
    
    distances = []
    for order in remaining_orders:
        total_distance = 0
        for existing_order in current_bundle:
            pickup_distance = dist_mat[existing_order.id, order.id]
            delivery_distance = dist_mat[existing_order.id + K, order.id + K]
            total_distance += (pickup_distance + delivery_distance)
        average_distance = total_distance / bundle_size
        distances.append((order, average_distance))
    
    distances.sort(key=lambda x: x[1])
    nearest_orders = [order for order, _ in distances[:num_orders]]
    return nearest_orders

def classify_orders_by_volume(all_orders):
    volumes = [order.volume for order in all_orders]
    avg_volume = np.mean(volumes)
    small_orders = [order for order in all_orders if order.volume < avg_volume * 1.5]
    large_orders = [order for order in all_orders if order.volume >= avg_volume * 1.5]
    return small_orders, large_orders

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, small_orders, large_orders):
    bundles = []
    remaining_orders = orders[:]
    assigned_order_ids = set()  # 주문 할당 추적을 위한 집합
    
    while remaining_orders and rider.available_number > 0:
        if rider.type == 'WALK' and small_orders:
            current_order = random.choice(small_orders)
            small_orders.remove(current_order)
        elif rider.type == 'BIKE' and small_orders:
            current_order = random.choice(small_orders)
            small_orders.remove(current_order)
        elif rider.type == 'CAR' and large_orders:
            current_order = random.choice(large_orders)
            large_orders.remove(current_order)
        else:
            current_order = random.choice(remaining_orders)
            remaining_orders.remove(current_order)
        
        current_bundle = [current_order]
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
        is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
        if is_feasible != 0:
            remaining_orders.append(current_order)
            return bundles, remaining_orders
        
        assigned_order_ids.add(current_order.id)
        current_volume = current_order.volume
        current_time = current_order.ready_time

        while True:
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 30)
            added = False

            if len(current_bundle) >= 4:
                break
            
            for next_order in nearest_orders:
                if current_volume + next_order.volume > rider.capa or next_order.id in assigned_order_ids:
                    continue
                
                current_bundle_ids = [o.id for o in current_bundle]
                next_bundle_ids = [next_order.id]

                combined_ids = current_bundle_ids + next_bundle_ids
                pickup_permutations = itertools.permutations(combined_ids)

                valid_combinations = []
                
                for perm_shop_seq in pickup_permutations:
                    delivery_permutations = itertools.permutations(perm_shop_seq)
                    for perm_dlv_seq in delivery_permutations:
                        new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), current_volume + next_order.volume, 0)
                        new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
                        new_bundle.update_cost()

                        is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
                        if is_feasible == 0:
                            valid_combinations.append((list(perm_shop_seq), list(perm_dlv_seq)))

                if valid_combinations:
                    best_combination = min(valid_combinations, key=lambda x: get_total_distance(K, dist_mat, x[0], x[1]))
                    best_shop_seq, best_dlv_seq = best_combination

                    current_bundle.append(next_order)
                    current_volume += next_order.volume
                    current_time += rider.T[current_bundle[-2].id, next_order.id]
                    remaining_orders.remove(next_order)
                    assigned_order_ids.add(next_order.id)
                    added = True

                    shop_seq = best_shop_seq
                    delivery_seq = best_dlv_seq
                    break

            if not added:
                break

        final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def weighted_random_choice(riders, weights):
    total = sum(weights)
    cumulative_weights = [sum(weights[:i+1]) for i in range(len(weights))]
    r = random.uniform(0, total)
    for rider, cumulative_weight in zip(riders, cumulative_weights):
        if r < cumulative_weight:
            return rider

def get_rider_weights(riders):
    weights = []
    for rider in riders:
        if rider.type == 'WALK':
            weights.append(2)  # 도보 라이더 가중치
        elif rider.type == 'BIKE':
            weights.append(3)  # 바이크 라이더 가중치
        else:
            weights.append(1)  # 자동차 라이더 가중치
    return weights

def try_merging_single_order_bundles(all_bundles, all_orders, dist_mat, K):
    single_order_bundles = [bundle for bundle in all_bundles if len(bundle.shop_seq) == 1]
    merged_bundles = []

    while single_order_bundles:
        bundle1 = single_order_bundles.pop(0)
        best_merge = None
        best_cost = float('inf')

        for bundle2 in single_order_bundles:
            combined_orders = bundle1.shop_seq + bundle2.shop_seq
            pickup_permutations = permutations(combined_orders)

            for perm_shop_seq in pickup_permutations:
                for perm_dlv_seq in permutations(perm_shop_seq):
                    new_bundle = Bundle(all_orders, bundle1.rider, list(perm_shop_seq), list(perm_dlv_seq), get_total_volume(all_orders, list(perm_shop_seq)), 0)
                    new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
                    new_bundle.update_cost()

                    if test_route_feasibility(all_orders, bundle1.rider, list(perm_shop_seq), list(perm_dlv_seq)) == 0:
                        if new_bundle.cost < best_cost:
                            best_merge = new_bundle
                            best_cost = new_bundle.cost

        if best_merge:
            merged_bundles.append(best_merge)
            single_order_bundles.remove(bundle2)
        else:
            merged_bundles.append(bundle1)

    return [bundle for bundle in all_bundles if len(bundle.shop_seq) > 1] + merged_bundles

def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    sorted_orders = random.sample(all_orders, len(all_orders))

    all_riders_list = all_riders
    print(all_riders_list)

    all_bundles = []

    small_orders, large_orders = classify_orders_by_volume(all_orders)

    while sorted_orders and all_riders_list:
        weights = get_rider_weights(all_riders_list)
        rider = weighted_random_choice(all_riders_list, weights)
        
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders, small_orders, large_orders)
            for bundle in bundles:
                all_bundles.append(bundle)

    all_bundles = try_merging_single_order_bundles(all_bundles, all_orders, dist_mat, K)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution, best_obj

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    for i, result in enumerate(results):
        solution, obj_value = result
        print(f'Objective value from process {i+1}: {obj_value}')
    
    best_solution = min(results, key=lambda x: x[1])
    return best_solution[0]
