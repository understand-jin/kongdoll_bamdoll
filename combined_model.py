import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
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


def assign_orders_to_rider2(all_riders_list, effectiveness_indicator, sorted_orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = sorted_orders[:]
    
    # 라이더 타입별 사용된 수를 추적하기 위한 딕셔너리 초기화
    used_riders = {rider.type: 0 for rider in all_riders_list}
    
    while remaining_orders:
        # 유효한 라이더를 선택할 때까지 반복
        while True:
            rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
            if rider.available_number > 0:
                rider.available_number -= 1  # 라이더 사용 시 available_number 감소
                used_riders[rider.type] += 1  # 선택된 라이더 타입의 사용된 수를 증가
                break
        
        current_order = remaining_orders.pop(0)
        current_bundle = [current_order]
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
        # 번들을 만들기 위해 루프를 돌며 유효한 라이더를 찾기
        while True:
            is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
            if is_feasible == 0:
                break  # 유효한 라이더를 찾았으면 루프 종료
            else:
                # 유효하지 않은 라이더의 available_number 복원
                rider.available_number += 1
                used_riders[rider.type] -= 1  # 사용된 라이더 수 감소
                
                # 다른 라이더를 다시 시도
                while True:
                    rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
                    if rider.available_number > 0:
                        rider.available_number -= 1  # 라이더 사용 시 available_number 감소
                        used_riders[rider.type] += 1  # 사용된 라이더 수 증가
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

    # 사용된 라이더의 수를 따로 반환
    return bundles, remaining_orders, used_riders




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
        associated_bundles = set()
        for order_id in nearest_order_ids:
            for bundle in remaining_solution:
                if order_id in bundle.shop_seq:
                    associated_bundles.add(bundle)
                    break

        # nearest_order_ids 중 번들에 포함되지 않은 주문이 있는지 확인
        missing_orders = set(nearest_order_ids) - {order_id for bundle in associated_bundles for order_id in bundle.shop_seq}
        for order_id in missing_orders:
            for bundle in best_solution:
                if order_id in bundle.shop_seq:
                    associated_bundles.add(bundle)
                    break

        # 현재 번들과 찾은 번들을 합침
        candidate_bundles = list(associated_bundles)

        # candidate_bundles의 rider 객체를 all_riders 리스트에서 찾아 업데이트
        print(f"candidate_bundles : {candidate_bundles}")
        for bundle in candidate_bundles:
            for rider in all_riders:
                if rider.type == bundle.rider.type:
                    print(f"before : {rider.available_number}")
                    rider.available_number += 1
                    print(f"after : {rider.available_number}")

        candidate_order_ids = list(set(order_id for bundle in candidate_bundles for order_id in bundle.shop_seq))

        # best_solution에서 candidate_bundles에 있는 번들을 제거
        remaining_solution = [
            bundle for bundle in remaining_solution 
            if not any(order_id in bundle.shop_seq for order_id in candidate_order_ids)
        ]

        # 모든 가용 가능한 라이더를 대상으로 효율성 계산
        effectiveness_indicator = calculate_efficiencies(K, all_riders, all_orders, dist_mat)

        # 모든 새로운 번들을 저장할 리스트
        all_new_bundles = []

        # candidate_order_ids가 비워질 때까지 assign_orders_to_rider2 반복 호출
        while candidate_order_ids:
            print(f"all_riders : {all_riders}")
            new_bundles, remaining_orders, used_riders = assign_orders_to_rider2(all_riders, effectiveness_indicator, [all_orders[i] for i in candidate_order_ids], dist_mat, K, all_orders)
            all_new_bundles.extend(new_bundles)

            # 사용된 라이더의 available_number 감소
            # for rider_type, count in used_riders.items():
            #     for rider in all_riders:
            #         if rider.type == rider_type:
            #             rider.available_number -= count
            print(f"new_bundles : {all_new_bundles}")
            print(f"used_riders : {used_riders}")
            print(f"adjusted used_riders : {all_riders}")

            # remaining_orders가 있는 경우, candidate_order_ids를 갱신
            if remaining_orders:
                candidate_order_ids = list(set(order.id for order in remaining_orders))
            else:
                candidate_order_ids = []

        # 모든 새로운 번들이 생성된 후 기존 번들들과 비용 비교
        existing_total_cost = sum(bundle.cost for bundle in candidate_bundles)
        new_total_cost = sum(bundle.cost for bundle in all_new_bundles)
        print(f"final_new_bundles : {new_bundles}")
        check2 = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in remaining_solution
    ]

        print(f"remaining_solution final :  {check2}")

        if new_total_cost < existing_total_cost:
            remaining_solution.extend(all_new_bundles)
        else:
            remaining_solution.extend(candidate_bundles)

    # 최종 솔루션으로 업데이트
    final_solution = remaining_solution
    final_solution_cost = sum(bundle.cost for bundle in final_solution)

    return final_solution





# def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
#     start_time = time.time()

#     for r in all_riders:
#         r.T = np.round(dist_mat / r.speed + r.service_time)

#     # 효율성 지표 계산
#     effectiveness_indicator = calculate_efficiencies(K, all_riders, all_orders, dist_mat)
#     effectiveness_dict = {rider.type: effectiveness for rider, effectiveness in zip(all_riders, effectiveness_indicator)}

#     # 주문들을 무작위로 섞기
#     sorted_orders = random.sample(all_orders, len(all_orders))

#     all_bundles = []

#     all_riders_list = all_riders

#     # while sorted_orders:
#     #     # 라이더와 주문 할당
#     #     bundles, sorted_orders = assign_orders_to_rider(all_riders, effectiveness_indicator, sorted_orders, dist_mat, K, all_orders)
#     #     all_bundles.extend(bundles)

#     while sorted_orders and all_riders_list:
#         rider = assign_riders_with_weighted_probability(all_riders_list, effectiveness_indicator)
#         if rider.available_number > 0:
#             bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
#             for bundle in bundles:
#                 all_bundles.append(bundle)

#     best_obj = sum((bundle.cost for bundle in all_bundles)) / K
#     print(f'Initial best obj = {best_obj}')

#     return all_bundles, best_obj

def count_riders_by_type(best_solution):
    rider_count = {
        'BIKE': 0,
        'WALK': 0,
        'CAR': 0
    }
    
    for bundle in best_solution:
        rider_type = bundle.rider.type
        if rider_type in rider_count:
            rider_count[rider_type] += 1
    
    return rider_count


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
    infeasibility = None

    for bundle in solution:
        rider_type, shop_seq, dlv_seq = bundle.rider.type, bundle.shop_seq, bundle.dlv_seq
        
        # 라이더 사용량 카운트
        rider_usage[rider_type] += 1

        # 주어진 라이더 수를 초과하는지 확인
        rider = next(r for r in all_riders if r.type == rider_type)
        if rider_usage[rider_type] > rider.available_number:
            infeasibility = f'The number of used riders of type {rider_type} exceeds the given available limit!'
            break

        # 주문이 중복되었거나 누락되었는지 확인
        for order_id in dlv_seq:
            if order_id in assigned_orders:
                infeasibility = f"Order {order_id} is assigned more than once."
                break
            assigned_orders.add(order_id)
        
        if infeasibility:
            break

    # 모든 주문이 정확히 한 번씩 할당되었는지 확인
    if infeasibility is None and len(assigned_orders) != K:
        infeasibility = "Not all orders are assigned."

    # 원래 all_riders의 available_number와 optimized_solution에 주문을 할당받은 라이더들의 수를 비교
    if infeasibility is None:
        for rider in all_riders:
            if rider_usage[rider.type] > rider.available_number:
                infeasibility = f'The number of used riders of type {rider.type} exceeds the given available limit!'
                break

    if infeasibility:
        print(f"Infeasibility found: {infeasibility}")
        return False
    else:
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
        if rider.type == '도보':
            weights.append(1)  # 도보 라이더 가중치
        elif rider.type == '바이크':
            weights.append(2)  # 바이크 라이더 가중치
        else:
            weights.append(3)  # 자동차 라이더 가중치
    return weights

def find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, num_orders=30):
    bundle_size = len(current_bundle)
    
    distances = []
    for order in remaining_orders:
        total_distance = 0
        for existing_order in current_bundle:
            pickup_distance = dist_mat[existing_order.id, order.id]
            delivery_distance = dist_mat[existing_order.id + K, order.id + K]
            total_distance += (pickup_distance + delivery_distance)
        
        last_pickup_to_first_delivery = dist_mat[current_bundle[-1].id, order.id + K]
        new_delivery_distance = dist_mat[order.id + K, order.id + K]
        
        average_distance = (total_distance + last_pickup_to_first_delivery + new_delivery_distance) / (bundle_size + 1)
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
        
        current_total_volume = current_order.volume
        current_time = current_order.ready_time

        while True:
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K)
            added = False

            if len(current_bundle) >= 4:
                break
            
            for next_order in nearest_orders:
                if current_total_volume + next_order.volume > rider.capa:
                    continue
                
                current_bundle_ids = [o.id for o in current_bundle]
                next_bundle_ids = [next_order.id]

                combined_ids = current_bundle_ids + next_bundle_ids
                pickup_permutations = itertools.permutations(combined_ids)

                valid_combinations = []
                
                for perm_shop_seq in pickup_permutations:
                    delivery_permutations = itertools.permutations(perm_shop_seq)
                    for perm_dlv_seq in delivery_permutations:
                        new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), current_total_volume + next_order.volume, 0)
                        new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
                        new_bundle.update_cost()

                        is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
                        if is_feasible == 0:
                            valid_combinations.append((list(perm_shop_seq), list(perm_dlv_seq)))

                if valid_combinations:
                    best_combination = min(valid_combinations, key=lambda x: get_total_distance(K, dist_mat, x[0], x[1]))
                    best_shop_seq, best_dlv_seq = best_combination

                    current_bundle.append(next_order)
                    current_total_volume += next_order.volume
                    current_time += rider.T[current_bundle[-2].id, next_order.id]
                    remaining_orders.remove(next_order)
                    added = True

                    # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
                    shop_seq = best_shop_seq
                    delivery_seq = best_dlv_seq
                    break

            if not added:
                break

        final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_total_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def reassign_riders_to_bundles(bundles, all_riders, all_orders, dist_mat, K):
    for bundle in bundles:
        best_cost = float('inf')
        best_rider = None
        best_shop_seq = None
        best_dlv_seq = None

        # 최적의 라이더와 비용을 찾습니다.
        for rider in all_riders:
            if bundle.total_volume <= rider.capa:
                permuted_sequences = itertools.permutations(bundle.shop_seq)
                for shop_seq in permuted_sequences:
                    for dlv_seq in itertools.permutations(shop_seq):
                        if test_route_feasibility(all_orders, rider, shop_seq, dlv_seq) == 0:
                            total_distance = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
                            total_cost = rider.fixed_cost + (total_distance / 100.0) * rider.var_cost
                            if total_cost < best_cost:
                                best_cost = total_cost
                                best_rider = rider
                                best_shop_seq = list(shop_seq)
                                best_dlv_seq = list(dlv_seq)

        # 최적의 라이더의 가용수가 없을 경우 처리
        if best_rider:
            if best_rider.available_number <= 0:
                # 현재 최적의 라이더가 처리한 번들 중에서 현재 번들보다 비용이 큰 번들을 찾습니다.
                current_rider_bundles = [b for b in bundles if b.rider == best_rider]
                expensive_bundles = [b for b in current_rider_bundles if b.cost > best_cost]
                
                # 가장 비용이 높은 번들부터 다른 라이더로 변경하려고 시도합니다.
                expensive_bundles.sort(key=lambda b: b.cost, reverse=True)
                
                for exp_bundle in expensive_bundles:
                    if exp_bundle == bundle:
                        continue  # 현재 번들은 제외
                    
                    # 새로운 라이더로 변경 시도
                    new_best_cost = float('inf')
                    new_best_rider = None
                    new_best_shop_seq = None
                    new_best_dlv_seq = None
                    
                    for rider in all_riders:
                        if rider.available_number > 0 and exp_bundle.total_volume <= rider.capa:
                            permuted_sequences = itertools.permutations(exp_bundle.shop_seq)
                            for shop_seq in permuted_sequences:
                                for dlv_seq in itertools.permutations(shop_seq):
                                    if test_route_feasibility(all_orders, rider, shop_seq, dlv_seq) == 0:
                                        total_distance = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
                                        total_cost = rider.fixed_cost + (total_distance / 100.0) * rider.var_cost
                                        if total_cost < new_best_cost:
                                            new_best_cost = total_cost
                                            new_best_rider = rider
                                            new_best_shop_seq = list(shop_seq)
                                            new_best_dlv_seq = list(dlv_seq)
                    if new_best_rider:
                        # 번들을 새로운 라이더로 변경
                        exp_bundle.rider = new_best_rider
                        exp_bundle.shop_seq = new_best_shop_seq
                        exp_bundle.dlv_seq = new_best_dlv_seq
                        exp_bundle.total_dist = get_total_distance(K, dist_mat, new_best_shop_seq, new_best_dlv_seq)
                        exp_bundle.update_cost()
                        new_best_rider.available_number -= 1
                        # 변경이 성공적으로 이루어진 후, 최적의 라이더를 현재 번들에 할당
                        bundle.rider = best_rider
                        bundle.shop_seq = best_shop_seq
                        bundle.dlv_seq = best_dlv_seq
                        bundle.total_dist = get_total_distance(K, dist_mat, best_shop_seq, best_dlv_seq)
                        bundle.update_cost()
                        best_rider.available_number -= 1
                        break  # 번들 할당이 완료되면 더 이상의 번들 변경은 필요 없음
            else:
                # 최적의 라이더가 가용한 경우, 현재 번들에 할당
                bundle.rider = best_rider
                bundle.shop_seq = best_shop_seq
                bundle.dlv_seq = best_dlv_seq
                bundle.total_dist = get_total_distance(K, dist_mat, best_shop_seq, best_dlv_seq)
                bundle.update_cost()
                best_rider.available_number -= 1


def single_run_algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    sorted_orders = random.sample(all_orders, len(all_orders))
    all_riders_list = all_riders
    all_bundles = []

    while sorted_orders and all_riders_list:
        weights = get_rider_weights(all_riders_list)
        rider = weighted_random_choice(all_riders_list, weights)
        
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
            for bundle in bundles:
                all_bundles.append(bundle)

    reassign_riders_to_bundles(all_bundles, all_riders, all_orders, dist_mat, K)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    # solution = [
    #     [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
    #     for bundle in all_bundles
    # ]

    return all_bundles, best_obj

# def algorithm2(K, all_orders, all_riders, dist_mat, timelimit=60, num_processes=30):
#     with concurrent.futures.ProcessPoolExecutor(max_workers=num_processes) as executor:
#         futures = [executor.submit(single_run_algorithm, K, all_orders, all_riders, dist_mat, timelimit) for _ in range(num_processes)]
#         results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
#     for i, result in enumerate(results):
#         solution, obj_value = result
#         print(f'Objective value from process {i+1}: {obj_value}')
    
#     best_solution = min(results, key=lambda x: x[1])
#     return best_solution[0]


