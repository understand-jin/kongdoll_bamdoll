import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
import concurrent.futures

def calculate_efficiencies(K, all_riders, all_orders, dist_mat):
    # 모든 주문의 부피 평균 계산
    order_volumes = [order.volume for order in all_orders]
    avg_volume = np.mean(order_volumes)

    # d1, d2, d3 계산
    d1 = np.sum(dist_mat[:K, :K]) / 2500
    d2 = np.sum(dist_mat[:K, K:2*K]) / 2500
    d3 = np.sum(dist_mat[K:2*K, K:2*K]) / 2500

    # 각 배달원의 효율성 지표 계산 함수
    def calculate_efficiency(rider, avg_volume, d1, d2, d3):
        capacity = rider.capa
        variable_cost = rider.var_cost
        fixed_cost = rider.fixed_cost
        
        Ri = (0.8 * capacity) / avg_volume
        Xi = (Ri - 1) * d1 + (Ri - 1) * d3 + d2
        efficiency = fixed_cost + (Xi / 100) * variable_cost
        
        return efficiency

    # 각 배달원의 효율성 지표 계산
    efficiencies = []
    for rider in all_riders:
        rider_type = rider.type
        efficiency = calculate_efficiency(rider, avg_volume, d1, d2, d3)
        efficiencies.append([rider_type, efficiency])

    # 효율성 지표 반환
    return efficiencies

def find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, num_orders):
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

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, all_riders):
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
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 50)
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

def assign_riders_with_weighted_probability(riders, effectiveness_indicator):
    total_effectiveness = sum([indicator[1] for indicator in effectiveness_indicator])
    weights = [total_effectiveness / indicator[1] for indicator in effectiveness_indicator]
    selected_rider = random.choices(riders, weights=weights, k=1)[0]
    return selected_rider



def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 효율성 지표 계산
    effectiveness_indicator = calculate_efficiencies(K, all_riders, all_orders, dist_mat)

    # 주문들을 무작위로 섞어 정렬
    sorted_orders = random.sample(all_orders, len(all_orders))

    # 모든 라이더를 합쳐서 처리
    all_riders_list = all_riders

    all_bundles = []

    while sorted_orders and all_riders_list:
        rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders, all_riders)
            for bundle in bundles:
                all_bundles.append(bundle)

    # 최적의 비용 계산
    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Optimized obj after merging single-order bundles = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution, best_obj


# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=61):
#     with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
#         futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
#         results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
#     # 각 프로세스의 목적함수 출력
#     for i, result in enumerate(results):
#         solution, obj_value = result
#         print(f'Objective value from process {i+1}: {obj_value}')
    
#     # 최적의 solution 선택
#     best_solution = min(results, key=lambda x: x[1])
#     return best_solution[0]

# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=61):
#     start_time = time.time()  # 시작 시간 기록
#     best_solution = None
#     best_obj_value = float('inf')  # 초기화할 때 무한대 값을 설정
    
#     def run_algorithm_with_timeout():
#         nonlocal best_solution, best_obj_value
#         with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
#             futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
#             try:
#                 for future in concurrent.futures.as_completed(futures, timeout=timelimit - (time.time() - start_time)):
#                     solution, obj_value = future.result()
#                     print(f'Objective value from process: {obj_value}')
#                     if obj_value < best_obj_value:
#                         best_obj_value = obj_value
#                         best_solution = solution
#             except concurrent.futures.TimeoutError:
#                 print("Time limit reached, returning the best solution found so far.")
    
#     run_algorithm_with_timeout()
    
#     return best_solution

def local_search(all_bundles, dist_mat, all_orders, K, max_iter=100):
    best_bundles = all_bundles[:]
    best_obj = sum((bundle.cost for bundle in best_bundles)) / K

    for _ in range(max_iter):
        # 번들 중 두 개를 무작위로 선택하여 병합 시도
        bundle1, bundle2 = random.sample(best_bundles, 2)
        new_bundle = try_merging_bundles(K, dist_mat, all_orders, bundle1, bundle2)

        if new_bundle is not None:
            # 병합 성공 시 기존 번들 제거하고 새 번들 추가
            best_bundles.remove(bundle1)
            bundle1.rider.available_number += 1

            best_bundles.remove(bundle2)
            bundle2.rider.available_number += 1

            best_bundles.append(new_bundle)
            new_bundle.rider.available_number -= 1

            cur_obj = sum((bundle.cost for bundle in best_bundles)) / K
            if cur_obj < best_obj:
                best_obj = cur_obj
                print(f'Improved obj = {best_obj}')
            else:
                # 개선되지 않으면 번들 원상복구
                best_bundles.remove(new_bundle)
                best_bundles.append(bundle1)
                bundle1.rider.available_number -= 1
                best_bundles.append(bundle2)
                bundle2.rider.available_number -= 1

    return best_bundles, best_obj

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=61):
    start_time = time.time()  # 시작 시간 기록
    best_solution = None
    best_obj_value = float('inf')  # 초기화할 때 무한대 값을 설정
    
    def run_algorithm_with_timeout():
        nonlocal best_solution, best_obj_value
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
            try:
                for future in concurrent.futures.as_completed(futures, timeout=timelimit - (time.time() - start_time)):
                    solution, obj_value = future.result()
                    print(f'Objective value from process: {obj_value}')
                    if obj_value < best_obj_value:
                        best_obj_value = obj_value
                        best_solution = solution
            except concurrent.futures.TimeoutError:
                print("Time limit reached, returning the best solution found so far.")
    
    run_algorithm_with_timeout()

    # local search를 통해 best_solution을 더 개선
    improved_bundles, improved_obj = local_search(best_solution, dist_mat, all_orders, K)

    improved_solution = [
    [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
    for bundle in improved_bundles
]
    print(f'Final obj after local search = {improved_obj}')
    
    return improved_solution

