import numpy as np
import time
import random
from itertools import permutations
from util import Bundle, get_pd_times, try_merging_bundles, get_total_distance, get_total_volume, get_cheaper_available_riders, try_bundle_rider_changing

def find_nearest_orders(first_order, remaining_orders, dist_mat, K, num_orders=10):
    distances = [(order, dist_mat[first_order.id, order.id] + dist_mat[first_order.id + K, order.id + K]) for order in remaining_orders]
    distances.sort(key=lambda x: x[1])
    nearest_orders = [order for order, dist in distances[:num_orders]]
    return nearest_orders

def assign_orders_to_rider(riders, orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = orders[:]
    
    # 가용 가능한 라이더 수 초기화
    # rider_available_numbers = {
    #     'BIKE': sum(r.available_number for r in riders if r.type == 'BIKE'),
    #     'CAR': sum(r.available_number for r in riders if r.type == 'CAR'),
    #     'WALK': sum(r.available_number for r in riders if r.type == 'WALK')
    # }
    bike_riders = [r for r in riders if r.type == 'BIKE']
    car_riders = [r for r in riders if r.type == 'CAR']
    walk_riders = [r for r in riders if r.type == 'WALK']



    print(f"Initial rider availability: {rider_available_numbers}")

    while remaining_orders and sum(rider_available_numbers.values()) > 0:
        # 첫 번째 주문 선택
        current_order = remaining_orders.pop(0)
        shop_seq = [current_order.id]
        delivery_seq = sorted(shop_seq, key=lambda order_id: all_orders[order_id].deadline)

        # 라이더를 랜덤하게 선택하고 feasible한지 확인
        feasible_rider = None
        random.shuffle(riders)
        print("check1")
        for rider in riders:
            if rider_available_numbers[rider.type] > 0:
                print(f"Testing feasibility for rider: {rider.type} with available number: {rider.available_number}")
                print(f"Rider details: {rider}")
                print(f"Shop sequence: {shop_seq}")
                print(f"Delivery sequence: {delivery_seq}")
                is_feasible = test_route_feasibility(all_orders, rider, shop_seq, delivery_seq)
                print(f"Feasibility result: {is_feasible}")
                if is_feasible == 0:
                    feasible_rider = rider
                    break
        
        if not feasible_rider:
            # 모든 라이더 유형에서 feasible하지 않으면 리턴
            print(f"No feasible rider found for order: {current_order.id}")
            remaining_orders.insert(0, current_order)
            return bundles, remaining_orders
        
        print("check2")
        # feasible한 경우 번들에 추가
        current_bundle = [current_order]
        current_volume = current_order.volume
        current_time = current_order.ready_time
        first_order = current_order  # 첫 번째 주문을 저장

        nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)

        print("4")
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
        rider_available_numbers[feasible_rider.type] -= 1  # 가용 가능한 라이더 수 감소

    return bundles, remaining_orders


def test_route_feasibility(all_orders, rider, shop_seq, dlv_seq):

    print(f"Inside test_route_feasibility: {rider}, {shop_seq}, {dlv_seq}")

    total_vol = get_total_volume(all_orders, shop_seq)
    print(f"total_vol : {total_vol}")
    if total_vol > rider.capa:
        # Capacity overflow!
        return -1 # Capacity infeasibility
    
    pickup_times, dlv_times = get_pd_times(all_orders, rider, shop_seq, dlv_seq)
    print(f"dlv_times : {dlv_times}")
    for k, dlv_time in dlv_times.items():
        if dlv_time > all_orders[k].deadline:
            return -2 # Deadline infeasibility
    print("4")
    return 0

