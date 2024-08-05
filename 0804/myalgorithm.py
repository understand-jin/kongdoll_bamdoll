import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, solution_check, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
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

def assign_orders_to_rider(all_riders_list, effectiveness_indicator, sorted_orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = sorted_orders[:]
    
    # 유효한 라이더를 선택할 때까지 반복
    while True:
        rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
        if rider.available_number > 0:
            break

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

def assign_orders_to_rider2(all_riders_list, effectiveness_indicator, sorted_orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = sorted_orders[:]
    
    while remaining_orders:
        # 유효한 라이더를 선택할 때까지 반복
        while True:
            rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
            if rider.available_number > 0:
                break

        current_order = remaining_orders.pop(0)
        current_bundle = [current_order]
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
        # 번들을 만들기 위해 루프를 돌며 유효한 라이더를 찾기
        while True:
            is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
            if is_feasible == 0:
                break  # 유효한 라이더가 찾았으면 루프 종료
            else:
                # 유효하지 않은 라이더는 다시 시도
                while True:
                    rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
                    if rider.available_number > 0:
                        break

        # 유효한 라이더가 할당되면 나머지 번들 과정을 진행
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


def optimize_single_order_bundles(best_solution, all_orders, all_riders, dist_mat, K, max_nearest_bundles=5):
    single_order_bundles = [bundle for bundle in best_solution if len(bundle.shop_seq) == 1]
    remaining_solution = best_solution[:]  # best_solution을 복사하여 사용

    for single_bundle in single_order_bundles:
        single_order_id = single_bundle.shop_seq[0]
        single_order = all_orders[single_order_id]

        # 해당 주문에 가장 가까운 5개의 주문 찾기
        nearest_orders = find_nearest_orders([single_order], all_orders, dist_mat, K, max_nearest_bundles)
        nearest_order_ids = [order.id for order in nearest_orders]

        # 이 주문들이 들어가 있는 번들들 찾기
        associated_bundles = set()  # 중복을 피하기 위해 set 사용
        for order_id in nearest_order_ids:
            for bundle in remaining_solution:  # 남아 있는 솔루션에서 번들 찾기
                if order_id in bundle.shop_seq:
                    associated_bundles.add(bundle)
                    break

        # nearest_order_ids 중 번들에 포함되지 않은 주문이 있는지 확인
        missing_orders = set(nearest_order_ids) - {order_id for bundle in associated_bundles for order_id in bundle.shop_seq}

        # 모든 주문이 포함된 번들을 찾지 못한 경우 추가로 검색
        for order_id in missing_orders:
            for bundle in best_solution:
                if order_id in bundle.shop_seq:
                    associated_bundles.add(bundle)
                    break

        # 현재 번들과 찾은 번들을 합침 (단, single_bundle이 이미 associated_bundles에 있을 경우 제외)
        candidate_bundles = list(associated_bundles)  # set을 list로 변환
        if single_bundle not in associated_bundles:
            candidate_bundles.append(single_bundle)

        for bundle in candidate_bundles:
            bundle.rider.available_number += 1

        candidate_order_ids = list(set(order_id for bundle in candidate_bundles for order_id in bundle.shop_seq))  # 중복 제거

        # best_solution에서 candidate_bundles에 있는 번들을 제거
        remaining_solution = [bundle for bundle in remaining_solution if bundle not in candidate_bundles]

        # candidate_bundles에서 사용 중인 라이더들만 필터링
        involved_riders = {bundle.rider for bundle in candidate_bundles}

        # 주문들을 처리할 라이더와 할당된 주문들을 기반으로 번들 생성
        effectiveness_indicator = calculate_efficiencies(K, involved_riders, all_orders, dist_mat)
        
        # 모든 새로운 번들을 저장할 리스트
        all_new_bundles = []

        # candidate_order_ids가 비워질 때까지 assign_orders_to_rider 반복 호출
        while candidate_order_ids:
            print(f"candidate_order_ids : {candidate_order_ids}")
            new_bundles, remaining_orders = assign_orders_to_rider2(list(involved_riders), effectiveness_indicator, [all_orders[i] for i in candidate_order_ids], dist_mat, K, all_orders)
            print(f"new_bundles : {new_bundles}")
            print(f"remaining_order : {remaining_orders}")

            # new_bundles을 임시 리스트에 추가
            all_new_bundles.extend(new_bundles)

            # remaining_orders가 있는 경우, candidate_order_ids를 갱신
            if remaining_orders:
                candidate_order_ids = list(set(order.id for order in remaining_orders))
            else:
                candidate_order_ids = []

        # 모든 새로운 번들이 생성된 후 기존 번들들과 비용 비교
        existing_total_cost = sum(bundle.cost for bundle in candidate_bundles)
        new_total_cost = sum(bundle.cost for bundle in all_new_bundles)

        if new_total_cost < existing_total_cost:
            remaining_solution.extend(all_new_bundles)
        else:
            remaining_solution.extend(candidate_bundles)

    # 최종 솔루션으로 업데이트
    final_solution = remaining_solution

    # 최종 솔루션의 목적함수 계산 (총 비용)
    final_solution_cost = sum(bundle.cost for bundle in final_solution)

    return final_solution





def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 효율성 지표 계산
    effectiveness_indicator = calculate_efficiencies(K, all_riders, all_orders, dist_mat)
    effectiveness_dict = {rider.type: effectiveness for rider, effectiveness in zip(all_riders, effectiveness_indicator)}

    # 주문들을 무작위로 섞기
    sorted_orders = random.sample(all_orders, len(all_orders))

    all_bundles = []

    while sorted_orders:
        # 라이더와 주문 할당
        bundles, sorted_orders = assign_orders_to_rider(all_riders, effectiveness_indicator, sorted_orders, dist_mat, K, all_orders)
        all_bundles.extend(bundles)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    return all_bundles, best_obj


# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
#     with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
#         futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
#         results = [future.result() for future in concurrent.futures.as_completed(futures)]

#     # 각 프로세스의 목적함수 출력
#     for i, result in enumerate(results):
#         solution, obj_value = result
#         print(f'Objective value from process {i+1}: {obj_value}')

#     # 최적의 solution 선택
#     best_solution, best_obj_value = min(results, key=lambda x: x[1])
#     print(f"Best solution objective value: {best_obj_value}")
#     print(f"Best solution: {best_solution}")

#     # 단일 주문 번들을 최적화
#     optimized_solution = optimize_single_order_bundles(best_solution, all_orders, all_riders, dist_mat, K)

#     # 최종 solution 출력 형식으로 변환
#     final_solution = [
#         [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
#         for bundle in optimized_solution
#     ]

#     return final_solution

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
        futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    # 각 프로세스의 목적함수 출력
    for i, result in enumerate(results):
        solution, obj_value = result
        print(f'Objective value from process {i+1}: {obj_value}')

    # 최적의 solution 선택
    best_solution, best_obj_value = min(results, key=lambda x: x[1])
    print(f"Best solution objective value: {best_obj_value}")
    print(f"Best solution: {best_solution}")

    # 단일 주문 번들을 최적화
    optimized_solution = optimize_single_order_bundles(best_solution, all_orders, all_riders, dist_mat, K)

    # optimized_solution 유효성 체크
    if is_solution_feasible(K, all_orders, all_riders, optimized_solution):
        # optimized_solution 평균 비용 계산
        optimized_avg_cost = calculate_average_cost(optimized_solution, all_orders, all_riders, dist_mat, K)

        # 만약 optimized_solution이 더 낮은 평균 비용을 가지면, 그것을 선택
        if optimized_avg_cost < best_obj_value:
            print(f"Optimized solution is better with average cost: {optimized_avg_cost}")
            final_solution = [
                [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
                for bundle in optimized_solution
            ]
        else:
            print(f"Best solution remains better with average cost: {best_obj_value}")
            final_solution = [
                [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
                for bundle in best_solution
            ]
    else:
        # optimized_solution이 유효하지 않으면 best_solution 반환
        print("Optimized solution is not feasible. Returning best solution.")
        final_solution = [
            [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
            for bundle in best_solution
        ]

    return final_solution


def is_solution_feasible(K, all_orders, all_riders, solution):
    rider_usage = {rider.type: 0 for rider in all_riders}
    assigned_orders = set()

    for bundle in solution:
        rider_type, shop_seq, dlv_seq = bundle.rider.type, bundle.shop_seq, bundle.dlv_seq
        
        # 라이더 사용량 카운트
        rider_usage[rider_type] += 1

        # 주어진 라이더 수를 초과하는지 확인
        rider = next(r for r in all_riders if r.type == rider_type)
        if rider_usage[rider_type] > rider.available_number:
            print(f"Infeasibility: Too many {rider_type} riders used.")
            return False

        # 주문이 중복되었거나 누락되었는지 확인
        for order_id in dlv_seq:
            if order_id in assigned_orders:
                print(f"Infeasibility: Order {order_id} is assigned more than once.")
                return False
            assigned_orders.add(order_id)

    # 모든 주문이 정확히 한 번씩 할당되었는지 확인
    if len(assigned_orders) != K:
        print(f"Infeasibility: Not all orders are assigned.")
        return False

    return True

def calculate_average_cost(solution, all_orders, all_riders, dist_mat, K):
    total_cost = 0
    for bundle in solution:
        rider = next(r for r in all_riders if r.type == bundle.rider.type)
        dist = get_total_distance(K, dist_mat, bundle.shop_seq, bundle.dlv_seq)
        cost = rider.calculate_cost(dist)
        total_cost += cost
    average_cost = total_cost / K
    return average_cost
