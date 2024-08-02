import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, try_merging_bundles, get_total_distance, test_route_feasibility
import concurrent.futures

def normalize(values):
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [1] * len(values)
    return [(val - min_val) / (max_val - min_val) for val in values]

def select_rider_based_on_criteria(riders, all_orders, sorted_orders, dist_mat, K):
    weights = []
    for rider in riders:
        if rider.type == 'bike':
            ready_times = [order.ready_time for order in sorted_orders[:10]]
            norm_ready_times = normalize(ready_times)
            weight = 1 / rider.var_cost + sum(1 / t for t in norm_ready_times)
        elif rider.type == 'walk':
            distances = [dist_mat[order.id, order.id + K] for order in sorted_orders[:10]]
            norm_distances = normalize(distances)
            weight = 1 / rider.var_cost + sum(d for d in norm_distances)
        elif rider.type == 'car':
            volumes = [order.volume for order in sorted_orders[:10]]
            norm_volumes = normalize(volumes)
            weight = 1 / rider.var_cost + sum(v for v in norm_volumes)
        else:
            weight = 1 / rider.var_cost

        weights.append(weight)
    
    total_weight = sum(weights)
    probabilities = [weight / total_weight for weight in weights]
    
    # 상위 N개 라이더 중 무작위로 선택
    N = 100
    top_riders_indices = sorted(range(len(riders)), key=lambda i: probabilities[i], reverse=True)[:N]
    selected_index = random.choice(top_riders_indices)
    return riders[selected_index]

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

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = orders[:]
    
    while remaining_orders and rider.available_number > 0:
        current_order = remaining_orders.pop(0)
        current_bundle = [current_order]
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
        is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
        if is_feasible != 0:
            remaining_orders.insert(0, current_order)
            return bundles, remaining_orders
        
        current_volume = current_order.volume
        current_time = current_order.ready_time

        while True:
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 30)
            added = False

            if len(current_bundle) >= 4:
                break
            
            for next_order in nearest_orders:
                if current_volume + next_order.volume > rider.capa:
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
                    added = True

                    # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
                    shop_seq = best_shop_seq
                    delivery_seq = best_dlv_seq
                    break

            if not added:
                break

        final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 주문들을 ready_time 기준으로 정렬
    sorted_orders = random.sample(all_orders, len(all_orders))

    # 모든 라이더를 합쳐서 처리
    all_riders_list = all_riders
    print(all_riders_list)

    all_bundles = []

    while sorted_orders and all_riders_list:
        rider = select_rider_based_on_criteria(all_riders_list, all_orders, sorted_orders, dist_mat, K)
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
            for bundle in bundles:
                all_bundles.append(bundle)


    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')


    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution, best_obj

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=61):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 각 프로세스의 목적함수 출력
    for i, result in enumerate(results):
        solution, obj_value = result
        print(f'Objective value from process {i+1}: {obj_value}')
    
    # 최적의 solution 선택
    best_solution = min(results, key=lambda x: x[1])
    return best_solution[0]