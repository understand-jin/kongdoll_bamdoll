import numpy as np
import time
import itertools
import copy
import random
from itertools import permutations
from util import Bundle, get_avg_cost, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
import concurrent.futures

def calculate_efficiencies(K, all_riders, all_orders, dist_mat):
    # 모든 주문의 부피 평균 계산
    order_volumes = [order.volume for order in all_orders]
    avg_volume = np.mean(order_volumes)

    # d1, d2, d3 계산
    d1 = np.sum(dist_mat[:K, :K]) / (K*K)
    d2 = np.sum(dist_mat[:K, K:2*K]) / (K*K)
    d3 = np.sum(dist_mat[K:2*K, K:2*K]) / (K*K)

    # 각 배달원의 효율성 지표 계산 함수
    def calculate_efficiency(rider, avg_volume, d1, d2, d3):
        capacity = rider.capa
        variable_cost = rider.var_cost
        fixed_cost = rider.fixed_cost
        
        Ri = capacity / avg_volume
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

def assign_riders_with_weighted_probability(riders, effectiveness_indicator):
    total_effectiveness = sum([indicator[1] for indicator in effectiveness_indicator])
    weights = [total_effectiveness / indicator[1] for indicator in effectiveness_indicator]
    selected_rider = random.choices(riders, weights=weights, k=1)[0]
    return selected_rider


def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 효율성 지표 (예시로 임의의 값 사용)
    #effectiveness_indicator = [['bike', 100], ['car', 500], ['walk', 300]]
    effectiveness_indicator = calculate_efficiencies(K, all_riders, all_orders, dist_mat)
    effectiveness_dict = {rider.type: effectiveness for rider, effectiveness in zip(all_riders, effectiveness_indicator)}

    # 주문들을 ready_time 기준으로 정렬
    #sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)
    sorted_orders = random.sample(all_orders, len(all_orders))

    # 모든 라이더를 합쳐서 처리
    all_riders_list = all_riders

    all_bundles = []

    while sorted_orders and all_riders_list:
        rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
            for bundle in bundles:
                all_bundles.append(bundle)


    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    print(all_bundles)

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    print(f"solution : {solution}")

    return solution, best_obj

def create_bundles_from_solution(solution, all_orders, all_riders, dist_mat, K):
    bundles = []
    
    for rider_type, shop_seq, dlv_seq in solution:
        # 해당 라이더 타입에 맞는 라이더 객체 선택
        rider = next((r for r in all_riders if r.type == rider_type), None)
        if rider is None:
            continue  # 해당 타입의 라이더가 없는 경우, 다음으로 넘어감
        
        # 번들에 포함된 주문의 총 부피 계산
        total_volume = get_total_volume(all_orders, shop_seq)
        
        # 번들의 총 거리를 계산
        total_dist = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
        
        # 새로운 Bundle 객체 생성
        new_bundle = Bundle(all_orders, rider, shop_seq, dlv_seq, total_volume, total_dist)
        bundles.append(new_bundle)
    
    return bundles

# def first_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
#     with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
#         futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
#         results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
#     # 각 프로세스의 목적함수 출력
#     for i, result in enumerate(results):
#         solution, obj_value = result
#         print(f'Objective value from process {i+1}: {obj_value}')
    
#     # 최적의 solution 선택
#     best_solution = min(results, key=lambda x: x[1])
#     best_obj = get_avg_cost(all_orders, best_solution)

#     return best_solution[0]

def first_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # 각 프로세스의 목적함수 출력
    for i, result in enumerate(results):
        solution, obj_value = result
        print(f'Objective value from process {i+1}: {obj_value}')
    
    # 최적의 solution 선택
    best_solution, best_obj = min(results, key=lambda x: x[1])

    return best_solution, best_obj

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, tabu_tenure=5, max_iter=100):
    start_time = time.time()

    # 초기 해 생성
    best_solution, best_obj = first_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30)

    #best_solution, best_obj = single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60)

    # 현재 해와 그 목적 함수 값
    current_solution = create_bundles_from_solution(best_solution, all_orders, all_riders, dist_mat, K)
    current_obj = best_obj
    print(current_solution)

    # 금지 리스트 초기화
    tabu_list = []
    
    for _ in range(max_iter):
        # 시간 제한 체크
        if time.time() - start_time > timelimit:
            break
        
        # 이웃 해 생성
        neighbors = generate_neighbors(current_solution, all_orders, all_riders, dist_mat, K)
        
        # 금지되지 않은 최적의 이웃 해 찾기
        best_neighbor = None
        best_neighbor_obj = float('inf')
        
        for neighbor in neighbors:
            if neighbor not in tabu_list:
                # all_bundles을 구하는 함수 필요
                neighbor_obj = get_avg_cost(all_orders, neighbor)
                if neighbor_obj < best_neighbor_obj:
                    best_neighbor = neighbor
                    best_neighbor_obj = neighbor_obj
        
        # 금지 리스트 업데이트
        tabu_list.append(best_neighbor)
        if len(tabu_list) > tabu_tenure:
            tabu_list.pop(0)
        
        # 현재 해 갱신
        current_solution = best_neighbor
        current_obj = best_neighbor_obj
        
        # 최적 해 갱신
        if current_obj < best_obj:
            best_solution = current_solution
            best_obj = current_obj

        final_solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in best_solution
    ]
    
    return final_solution


def generate_neighbors(current_solution, all_orders, all_riders, dist_mat, K):
    neighbors = []

    # 번들 간의 주문 교환 시도
    for i in range(len(current_solution)):
        for j in range(i + 1, len(current_solution)):
            bundle1 = current_solution[i]
            bundle2 = current_solution[j]

            for order1 in bundle1.shop_seq:
                for order2 in bundle2.shop_seq:
                    # 번들 간 주문 교환
                    new_bundle1_shop_seq = bundle1.shop_seq.copy()
                    new_bundle2_shop_seq = bundle2.shop_seq.copy()

                    # 교환 적용
                    new_bundle1_shop_seq.remove(order1)
                    new_bundle1_shop_seq.append(order2)

                    new_bundle2_shop_seq.remove(order2)
                    new_bundle2_shop_seq.append(order1)

                    # 새로운 배달 순서 생성 (예시: 기한을 기준으로 정렬)
                    new_bundle1_dlv_seq = sorted(new_bundle1_shop_seq, key=lambda order_id: all_orders[order_id].deadline)
                    new_bundle2_dlv_seq = sorted(new_bundle2_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

                    # 새 번들에 포함된 주문의 총 부피 계산
                    new_bundle1_volume = get_total_volume(all_orders, new_bundle1_shop_seq)
                    new_bundle2_volume = get_total_volume(all_orders, new_bundle2_shop_seq)

                    # 새로운 번들의 총 거리를 계산
                    new_bundle1_total_dist = get_total_distance(K, dist_mat, new_bundle1_shop_seq, new_bundle1_dlv_seq)
                    new_bundle2_total_dist = get_total_distance(K, dist_mat, new_bundle2_shop_seq, new_bundle2_dlv_seq)

                    # 유효성 검증
                    feasible1 = test_route_feasibility(all_orders, bundle1.rider, new_bundle1_shop_seq, new_bundle1_dlv_seq)
                    feasible2 = test_route_feasibility(all_orders, bundle2.rider, new_bundle2_shop_seq, new_bundle2_dlv_seq)

                    if feasible1 == 0 and feasible2 == 0:
                        # 새로운 유효한 이웃 생성
                        new_solution = copy.deepcopy(current_solution)
                        new_solution[i] = Bundle(all_orders, bundle1.rider, new_bundle1_shop_seq, new_bundle1_dlv_seq, new_bundle1_volume, new_bundle1_total_dist)
                        new_solution[j] = Bundle(all_orders, bundle2.rider, new_bundle2_shop_seq, new_bundle2_dlv_seq, new_bundle2_volume, new_bundle2_total_dist)

                        neighbors.append(new_solution)

    return neighbors







