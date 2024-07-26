import numpy as np
import time
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

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
        first_order = current_order

        while True:
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 30)
            added = False
            
            for next_order in nearest_orders:
                if current_volume + next_order.volume > rider.capa:
                    continue
                
                current_bundle_ids = [o.id for o in current_bundle]
                next_bundle_ids = [next_order.id]

                combined_shop_seq = current_bundle_ids + next_bundle_ids
                combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

                new_bundle = Bundle(all_orders, rider, combined_shop_seq, combined_delivery_seq, current_volume + next_order.volume, 0)
                new_bundle.total_dist = get_total_distance(K, dist_mat, combined_shop_seq, combined_delivery_seq)
                new_bundle.update_cost()

                is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
                merged_bundle = None
                if is_feasible == 0:
                    merged_bundle = try_merging_bundles(K, dist_mat, all_orders, Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

                if merged_bundle is not None:
                    current_bundle.append(next_order)
                    current_volume += next_order.volume
                    current_time += rider.T[current_bundle[-2].id, next_order.id]
                    remaining_orders.remove(next_order)
                    added = True
                    break

            if not added:
                break
            # 번들에 주문이 추가될 때마다 nearest_orders 갱신
            nearest_orders = find_nearest_orders(current_bundle, remaining_orders, dist_mat, K, 30)

        shop_seq = [order.id for order in current_bundle]

        delivery_seq = shop_seq[:]
        delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
        best_dlv_seq = delivery_seq

        final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def assign_riders_with_weighted_probability(riders, effectiveness_indicator):
    total_effectiveness = sum([indicator[1] for indicator in effectiveness_indicator])
    weights = [total_effectiveness / indicator[1] for indicator in effectiveness_indicator]
    selected_rider = random.choices(riders, weights=weights, k=1)[0]
    return selected_rider

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 효율성 지표 (예시로 임의의 값 사용)
    effectiveness_indicator = [['bike', 100], ['car', 200], ['walk', 300]]
    effectiveness_dict = {rider.type: effectiveness for rider, effectiveness in zip(all_riders, effectiveness_indicator)}

    # 주문들을 ready_time 기준으로 정렬
    sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)

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

    while time.time() - start_time < timelimit:
        iter = 0
        max_merge_iter = 1000

        while iter < max_merge_iter and time.time() - start_time < timelimit:
            bundle1, bundle2 = select_two_bundles(all_bundles)
            new_bundle = try_merging_bundles(K, dist_mat, all_orders, bundle1, bundle2)
            if new_bundle is not None:
                is_feasible = test_route_feasibility(all_orders, new_bundle.rider, new_bundle.shop_seq, new_bundle.dlv_seq)
                if is_feasible == 0:
                    all_bundles.remove(bundle1)
                    bundle1.rider.available_number += 1

                    all_bundles.remove(bundle2)
                    bundle2.rider.available_number += 1

                    all_bundles.append(new_bundle)
                    new_bundle.rider.available_number -= 1

                    cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
                    if cur_obj < best_obj:
                        best_obj = cur_obj
                        print(f'New best obj after merge = {best_obj}')
            else:
                iter += 1

        for bundle in all_bundles:
            new_rider = get_cheaper_available_riders(all_riders, bundle.rider)
            if new_rider is not None and new_rider.available_number > 0:
                old_rider = bundle.rider
                temp_bundle = bundle
                if try_bundle_rider_changing(all_orders, dist_mat, temp_bundle, new_rider):
                    is_feasible = test_route_feasibility(all_orders, new_rider, temp_bundle.shop_seq, temp_bundle.dlv_seq)
                    if is_feasible == 0:
                        old_rider.available_number += 1
                        new_rider.available_number -= 1
                        bundle.rider = new_rider
                        bundle.shop_seq = temp_bundle.shop_seq
                        bundle.dlv_seq = temp_bundle.dlv_seq
                        bundle.update_cost()

        cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
        if cur_obj < best_obj:
            best_obj = cur_obj
            print(f'New best obj after rider reassignment = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution