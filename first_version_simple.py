import numpy as np
import time
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

def find_nearest_orders(first_order, remaining_orders, dist_mat, K, num_orders=10):
    distances = [(order, dist_mat[first_order.id, order.id] + dist_mat[first_order.id + K, order.id + K]) for order in remaining_orders]
    distances.sort(key=lambda x: x[1])
    nearest_orders = [order for order, dist in distances[:num_orders]]
    return nearest_orders

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = orders[:]
    
    while remaining_orders and rider.available_number > 0:
        # 첫 번째 주문 선택 및 feasibility 확인
        current_order = remaining_orders.pop(0)
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)
        
        # 번들이 feasible 한지 확인
        is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
        if is_feasible != 0:
            # feasible 하지 않으면 다른 라이더에게 할당하도록 리턴
            remaining_orders.insert(0, current_order)
            return bundles, remaining_orders
        
        # feasible 한 경우 번들에 추가
        current_bundle = [current_order]
        current_volume = current_order.volume
        current_time = current_order.ready_time
        first_order = current_order  # 첫 번째 주문을 저장

        nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)

        for next_order in nearest_orders:
            if current_volume + next_order.volume > rider.capa:
                continue
            
            # 현재 번들 및 새로운 주문을 번들로 만들어 배달 순서 정렬
            current_bundle_ids = [o.id for o in current_bundle]
            next_bundle_ids = [next_order.id]

            combined_shop_seq = current_bundle_ids + next_bundle_ids
            combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

            # 새로운 번들 생성
            new_bundle = Bundle(all_orders, rider, combined_shop_seq, combined_delivery_seq, current_volume + next_order.volume, 0)
            new_bundle.total_dist = get_total_distance(K, dist_mat, combined_shop_seq, combined_delivery_seq)
            new_bundle.update_cost()

            # 새로운 번들을 병합 테스트
            is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
            merged_bundle = None
            if is_feasible == 0:
                merged_bundle = try_merging_bundles(K, dist_mat, all_orders, Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

            if merged_bundle is not None:
                current_bundle.append(next_order)
                current_volume += next_order.volume
                current_time += rider.T[current_bundle[-2].id, next_order.id]
                remaining_orders.remove(next_order)
                break  # 번들에 추가하면 다음 주문으로 이동

        shop_seq = [order.id for order in current_bundle]

        # 배달 순서를 마감시간 기준으로 정렬
        delivery_seq = shop_seq[:]  # 초기 배달 순서는 픽업 순서와 동일
        delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
        best_dlv_seq = delivery_seq

        # 최종 번들 생성
        final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
        bundles.append(final_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 주문들을 ready_time 기준으로 정렬
    #sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)
    ready_times = np.array([order.ready_time for order in all_orders])
    weights = 1 / (ready_times + 1)  # 준비 시간이 짧을수록 높은 가중치 부여
    probabilities = weights / weights.sum()
    sorted_orders = list(np.random.choice(all_orders, size=len(all_orders), replace=False, p=probabilities))

    # A solution is a list of bundles
    solution = []

    # 라이더를 유형별로 나눔
    bike_riders = [r for r in all_riders if r.type == 'BIKE']
    car_riders = [r for r in all_riders if r.type == 'CAR']
    walk_riders = [r for r in all_riders if r.type == 'WALK']

    all_bundles = []

    # BIKE 라이더에게 우선 할당
    for bike_rider in bike_riders:
        if not sorted_orders:
            break
        if bike_rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(bike_rider, sorted_orders, dist_mat, K, all_orders)
            for bundle in bundles:
                #if test_route_feasibility(all_orders, bike_rider, bundle.shop_seq, bundle.dlv_seq) == 0:
                    all_bundles.append(bundle)

    # 남은 주문들을 CAR 또는 WALK 라이더에게 할당
    remaining_riders = car_riders + walk_riders
    random.shuffle(remaining_riders)
    while sorted_orders and remaining_riders:
        rider = remaining_riders.pop(0)
        if rider.available_number > 0:
            bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
            for bundle in bundles:
                #if test_route_feasibility(all_orders, rider, bundle.shop_seq, bundle.dlv_seq) == 0:
                    all_bundles.append(bundle)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution