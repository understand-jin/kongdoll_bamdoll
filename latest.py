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

# def find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, num_orders):
#     bundle_size = len(current_bundle)
    
#     distances = []
#     for order in remaining_orders:
#         total_distance = 0
#         for existing_order in current_bundle:
#             pickup_distance = dist_mat[existing_order.id, order.id]
#             delivery_distance = dist_mat[existing_order.id + K, order.id + K]
#             total_distance += (pickup_distance + delivery_distance)
#         average_distance = total_distance / bundle_size
#         distances.append((order, average_distance))
    
#     distances.sort(key=lambda x: x[1])
#     nearest_orders = [order for order, _ in distances[:num_orders]]
#     return nearest_orders

def find_nearest_orders(current_bundle, all_orders, dist_mat, K, num_orders):
    bundle_size = len(current_bundle)
    
    distances = []
    for order in all_orders:
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


# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, all_riders):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         current_order = remaining_orders.pop(0)
#         current_bundle = [current_order]
#         shop_seq = [current_order.id]
#         delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
#         is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
#         if is_feasible != 0:
#             remaining_orders.insert(0, current_order)
#             return bundles, remaining_orders
        
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         while True:
#             nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 50)
#             added = False

#             if len(current_bundle) >= 4:
#                 break
            
#             for next_order in nearest_orders:
#                 if current_volume + next_order.volume > rider.capa:
#                     continue
                
#                 current_bundle_ids = [o.id for o in current_bundle]
#                 next_bundle_ids = [next_order.id]

#                 combined_ids = current_bundle_ids + next_bundle_ids
#                 pickup_permutations = itertools.permutations(combined_ids)

#                 valid_combinations = []
                
#                 for perm_shop_seq in pickup_permutations:
#                     delivery_permutations = itertools.permutations(perm_shop_seq)
#                     for perm_dlv_seq in delivery_permutations:
#                         new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), current_volume + next_order.volume, 0)
#                         new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
#                         new_bundle.update_cost()

#                         is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
#                         if is_feasible == 0:
#                             valid_combinations.append((list(perm_shop_seq), list(perm_dlv_seq)))

#                 if valid_combinations:
#                     best_combination = min(valid_combinations, key=lambda x: get_total_distance(K, dist_mat, x[0], x[1]))
#                     best_shop_seq, best_dlv_seq = best_combination

#                     current_bundle.append(next_order)
#                     current_volume += next_order.volume
#                     current_time += rider.T[current_bundle[-2].id, next_order.id]
#                     remaining_orders.remove(next_order)
#                     added = True

#                     # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
#                     shop_seq = best_shop_seq
#                     delivery_seq = best_dlv_seq
#                     break

#             if not added:
#                 break

#         final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
#         bundles.append(final_bundle)
#         rider.available_number -= 1

#     return bundles, remaining_orders

# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, all_riders):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         current_order = remaining_orders.pop(0)
#         current_bundle = [current_order]
#         shop_seq = [current_order.id]
#         delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
#         is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
#         if is_feasible != 0:
#             remaining_orders.insert(0, current_order)
#             return bundles, remaining_orders
        
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         while True:
#             nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 50)
#             added = False

#             if len(current_bundle) >= 4:
#                 break
            
#             for next_order in nearest_orders:
#                 if current_volume + next_order.volume > rider.capa:
#                     continue
                
#                 # 이미 번들에 속해 있는지 확인
#                 existing_bundle = next((bundle for bundle in bundles if next_order.id in bundle.shop_seq or next_order.id in bundle.dlv_seq), None)

#                 if existing_bundle:
#                     # 기존 번들에서 next_order 제거
#                     original_shop_seq = existing_bundle.shop_seq[:]
#                     original_dlv_seq = existing_bundle.dlv_seq[:]
                    
#                     existing_bundle.shop_seq.remove(next_order.id)
#                     existing_bundle.dlv_seq.remove(next_order.id)
                    
#                     if not existing_bundle.shop_seq or not existing_bundle.dlv_seq:
#                         bundles.remove(existing_bundle)
#                     else:
#                         # 기존 번들 업데이트
#                         existing_bundle.total_dist = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq)
#                         existing_bundle.update_cost()

#                 current_bundle_ids = [o.id for o in current_bundle]
#                 next_bundle_ids = [next_order.id]

#                 combined_ids = current_bundle_ids + next_bundle_ids
#                 pickup_permutations = itertools.permutations(combined_ids)

#                 valid_combinations = []
                
#                 for perm_shop_seq in pickup_permutations:
#                     delivery_permutations = itertools.permutations(perm_shop_seq)
#                     for perm_dlv_seq in delivery_permutations:
#                         new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), current_volume + next_order.volume, 0)
#                         new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
#                         new_bundle.update_cost()

#                         is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
#                         if is_feasible == 0:
#                             valid_combinations.append((list(perm_shop_seq), list(perm_dlv_seq)))

#                 if valid_combinations:
#                     best_combination = min(valid_combinations, key=lambda x: get_total_distance(K, dist_mat, x[0], x[1]))
#                     best_shop_seq, best_dlv_seq = best_combination

#                     # 비용이 낮은지 확인
#                     original_bundle_cost = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq) * rider.var_cost + rider.fixed_cost if existing_bundle else 0
#                     new_original_bundle_cost = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq) * existing_bundle.rider.var_cost + existing_bundle.rider.fixed_cost if existing_bundle else 0
#                     current_bundle_cost = get_total_distance(K, dist_mat, shop_seq, delivery_seq) * rider.var_cost + rider.fixed_cost
#                     new_bundle_cost = get_total_distance(K, dist_mat, best_shop_seq, best_dlv_seq) * rider.var_cost + rider.fixed_cost
                    
#                     if not existing_bundle or (new_bundle_cost + new_original_bundle_cost) < (original_bundle_cost + current_bundle_cost):
#                         # 비용이 더 낮거나 기존 번들이 없는 경우 현재 번들에 추가
#                         current_bundle.append(next_order)
#                         current_volume += next_order.volume
#                         current_time += rider.T[current_bundle[-2].id, next_order.id]
#                         if next_order in remaining_orders:
#                             remaining_orders.remove(next_order)
#                         added = True

#                         # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
#                         shop_seq = best_shop_seq
#                         delivery_seq = best_dlv_seq
#                         break
#                     else:
#                         # 비용이 더 높은 경우 기존 번들에 다시 추가
#                         existing_bundle.shop_seq = original_shop_seq
#                         existing_bundle.dlv_seq = original_dlv_seq
#                         existing_bundle.total_dist = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq)
#                         existing_bundle.update_cost()

#             if not added:
#                 break

#         final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
#         bundles.append(final_bundle)
#         rider.available_number -= 1

#     return bundles, remaining_orders


# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, all_riders):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         current_order = remaining_orders.pop(0)
#         current_bundle = [current_order]
#         shop_seq = [current_order.id]
#         delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
#         is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
#         if is_feasible != 0:
#             remaining_orders.insert(0, current_order)
#             return bundles, remaining_orders
        
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         while True:
#             nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 50)
#             added = False

#             if len(current_bundle) >= 4:
#                 break
            
#             for next_order in nearest_orders:
#                 if current_volume + next_order.volume > rider.capa:
#                     continue
                
#                 # 이미 번들에 속해 있는지 확인
#                 existing_bundle = next((bundle for bundle in bundles if next_order.id in bundle.shop_seq or next_order.id in bundle.dlv_seq), None)

#                 if existing_bundle:
#                     # 기존 번들에서 next_order 제거
#                     original_shop_seq = existing_bundle.shop_seq[:]
#                     original_dlv_seq = existing_bundle.dlv_seq[:]
                    
#                     existing_bundle.shop_seq.remove(next_order.id)
#                     existing_bundle.dlv_seq.remove(next_order.id)
                    
#                     if not existing_bundle.shop_seq or not existing_bundle.dlv_seq:
#                         bundles.remove(existing_bundle)
#                     else:
#                         # 기존 번들 업데이트
#                         existing_bundle.total_dist = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq)
#                         existing_bundle.update_cost()

#                 current_bundle_ids = [o.id for o in current_bundle]
#                 next_bundle_ids = [next_order.id]

#                 combined_ids = current_bundle_ids + next_bundle_ids
#                 pickup_permutations = itertools.permutations(combined_ids)

#                 valid_combinations = []
                
#                 for perm_shop_seq in pickup_permutations:
#                     delivery_permutations = itertools.permutations(perm_shop_seq)
#                     for perm_dlv_seq in delivery_permutations:
#                         new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), current_volume + next_order.volume, 0)
#                         new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
#                         new_bundle.update_cost()

#                         is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
#                         if is_feasible == 0:
#                             valid_combinations.append((list(perm_shop_seq), list(perm_dlv_seq)))

#                 if valid_combinations:
#                     best_combination = min(valid_combinations, key=lambda x: get_total_distance(K, dist_mat, x[0], x[1]))
#                     best_shop_seq, best_dlv_seq = best_combination

#                     # 비용이 낮은지 확인
#                     original_bundle_cost = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq) * rider.var_cost + rider.fixed_cost if existing_bundle else 0
#                     new_original_bundle_cost = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq) * existing_bundle.rider.var_cost + existing_bundle.rider.fixed_cost if existing_bundle else 0
#                     current_bundle_cost = get_total_distance(K, dist_mat, shop_seq, delivery_seq) * rider.var_cost + rider.fixed_cost
#                     new_bundle_cost = get_total_distance(K, dist_mat, best_shop_seq, best_dlv_seq) * rider.var_cost + rider.fixed_cost
                    
#                     if not existing_bundle or (new_bundle_cost + new_original_bundle_cost) < (original_bundle_cost + current_bundle_cost):
#                         # 비용이 더 낮거나 기존 번들이 없는 경우 현재 번들에 추가
#                         current_bundle.append(next_order)
#                         current_volume += next_order.volume
#                         current_time += rider.T[current_bundle[-2].id, next_order.id]
#                         if next_order in remaining_orders:
#                             remaining_orders.remove(next_order)
#                         added = True

#                         # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
#                         shop_seq = best_shop_seq
#                         delivery_seq = best_dlv_seq
#                         break
#                     else:
#                         # 비용이 더 높은 경우 기존 번들에 다시 추가
#                         existing_bundle.shop_seq = original_shop_seq
#                         existing_bundle.dlv_seq = original_dlv_seq
#                         existing_bundle.total_dist = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq)
#                         existing_bundle.update_cost()

#             if not added:
#                 break

#         final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
#         bundles.append(final_bundle)
#         rider.available_number -= 1

#     # 단일 주문이 포함된 번들들을 병합
#     single_order_bundles = [bundle for bundle in bundles if len(bundle.shop_seq) == 1]
#     bundles = [bundle for bundle in bundles if len(bundle.shop_seq) > 1]

#     if len(single_order_bundles) > 1:
#         for i in range(len(single_order_bundles)):
#             for j in range(i + 1, len(single_order_bundles)):
#                 combined_ids = single_order_bundles[i].shop_seq + single_order_bundles[j].shop_seq
#                 combined_permutations = itertools.permutations(combined_ids)
                
#                 valid_combinations = []
#                 for perm_shop_seq in combined_permutations:
#                     perm_dlv_seq = perm_shop_seq  # 배송 순서는 여기서 동일하게 고려합니다.
#                     combined_volume = single_order_bundles[i].total_volume + single_order_bundles[j].total_volume
#                     if combined_volume <= rider.capa:
#                         new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), combined_volume, 0)
#                         new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
#                         new_bundle.update_cost()
#                         is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
#                         if is_feasible == 0:
#                             valid_combinations.append(new_bundle)

#                 if valid_combinations:
#                     best_new_bundle = min(valid_combinations, key=lambda x: x.total_dist)
#                     bundles.append(best_new_bundle)

#     return bundles, remaining_orders

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
                
                # 이미 번들에 속해 있는지 확인
                existing_bundle = next((bundle for bundle in bundles if next_order.id in bundle.shop_seq or next_order.id in bundle.dlv_seq), None)

                if existing_bundle:
                    # 기존 번들에서 next_order 제거
                    original_shop_seq = existing_bundle.shop_seq[:]
                    original_dlv_seq = existing_bundle.dlv_seq[:]
                    
                    existing_bundle.shop_seq.remove(next_order.id)
                    existing_bundle.dlv_seq.remove(next_order.id)
                    
                    if not existing_bundle.shop_seq or not existing_bundle.dlv_seq:
                        bundles.remove(existing_bundle)
                    else:
                        # 기존 번들 업데이트
                        existing_bundle.total_dist = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq)
                        existing_bundle.update_cost()

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

                    # 비용이 낮은지 확인
                    original_bundle_cost = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq) * rider.var_cost + rider.fixed_cost if existing_bundle else 0
                    new_original_bundle_cost = get_total_distance(K, dist_mat, existing_bundle.shop_seq, existing_bundle.dlv_seq) * existing_bundle.rider.var_cost + existing_bundle.rider.fixed_cost if existing_bundle else 0
                    current_bundle_cost = get_total_distance(K, dist_mat, shop_seq, delivery_seq) * rider.var_cost + rider.fixed_cost
                    new_bundle_cost = get_total_distance(K, dist_mat, best_shop_seq, best_dlv_seq) * rider.var_cost + rider.fixed_cost
                    
                    if not existing_bundle or (new_bundle_cost + new_original_bundle_cost) < (original_bundle_cost + current_bundle_cost):
                        # 비용이 더 낮거나 기존 번들이 없는 경우 현재 번들에 추가
                        current_bundle.append(next_order)
                        current_volume += next_order.volume
                        current_time += rider.T[current_bundle[-2].id, next_order.id]
                        if next_order in remaining_orders:
                            remaining_orders.remove(next_order)
                        added = True

                        # 선택된 best_shop_seq와 best_dlv_seq로 번들 갱신
                        shop_seq = best_shop_seq
                        delivery_seq = best_dlv_seq
                        break
                    else:
                        # 비용이 더 높은 경우 기존 번들에 다시 추가
                        existing_bundle.shop_seq = original_shop_seq
                        existing_bundle.dlv_seq = original_dlv_seq
                        existing_bundle.total_dist = get_total_distance(K, dist_mat, original_shop_seq, original_dlv_seq)
                        existing_bundle.update_cost()

            if not added:
                break

        final_bundle = Bundle(all_orders, rider, shop_seq, delivery_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, delivery_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    # 단일 주문이 포함된 번들들을 병합
    single_order_bundles = [bundle for bundle in bundles if len(bundle.shop_seq) == 1]
    #bundles = [bundle for bundle in bundles if len(bundle.shop_seq) > 1]

    if len(single_order_bundles) > 1:
        bundles_to_remove = []
        for i in range(len(single_order_bundles)):
            for j in range(i + 1, len(single_order_bundles)):
                combined_ids = single_order_bundles[i].shop_seq + single_order_bundles[j].shop_seq
                combined_permutations = itertools.permutations(combined_ids)
                
                valid_combinations = []
                for perm_shop_seq in combined_permutations:
                    perm_dlv_seq = perm_shop_seq  # 배송 순서는 동일하게 고려
                    combined_volume = single_order_bundles[i].total_volume + single_order_bundles[j].total_volume
                    if combined_volume <= rider.capa:
                        new_bundle = Bundle(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq), combined_volume, 0)
                        new_bundle.total_dist = get_total_distance(K, dist_mat, list(perm_shop_seq), list(perm_dlv_seq))
                        new_bundle.update_cost()
                        is_feasible = test_route_feasibility(all_orders, rider, list(perm_shop_seq), list(perm_dlv_seq))
                        if is_feasible == 0:
                            valid_combinations.append(new_bundle)

                if valid_combinations:
                    best_new_bundle = min(valid_combinations, key=lambda x: x.total_dist)
                    bundles.append(best_new_bundle)
                    
                    # 병합된 번들을 제거하기 위해 추가
                    bundles_to_remove.append(single_order_bundles[i])
                    bundles_to_remove.append(single_order_bundles[j])
                    print(bundles_to_remove)

                    bundles.remove(single_order_bundles[i])
                    bundles.remove(single_order_bundles[j])

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
    
    return best_solution



