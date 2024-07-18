import numpy as np
import time
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_cheaper_available_riders, try_bundle_rider_changing

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders):
    bundles = []
    remaining_orders = orders[:]
    while remaining_orders and rider.available_number > 0:
        current_order = remaining_orders.pop(0)
        current_bundle = [current_order]
        current_volume = current_order.volume
        current_time = current_order.ready_time

        first_order = current_order  # 첫 번째 주문을 저장

        while remaining_orders:
            next_order = None
            min_distance = float('inf')

            for order in remaining_orders:
                if current_volume + order.volume > rider.capa:
                    continue

                # 첫 번째 주문을 기준으로 거리 계산
                pickup_distance = dist_mat[first_order.id, order.id]
                delivery_distance = dist_mat[order.id, first_order.id + K]
                projected_time = current_time + rider.T[first_order.id, order.id] + rider.T[order.id, first_order.id + K]

                # 새로운 주문의 배달 완료 시간을 계산하고, 마감 시간보다 작은지 확인
                order_completion_time = current_time + rider.T[first_order.id, order.id] + rider.T[order.id, order.id + K]
                if order_completion_time > order.deadline:
                    continue

                total_distance = pickup_distance + delivery_distance
                if total_distance < min_distance:
                    # 임시 번들에 새로운 주문 추가
                    temp_bundle = current_bundle + [order]
                    temp_shop_seq = [o.id for o in temp_bundle]
                    feasible = False

                    # 가능한 모든 배달 순서 확인
                    for perm in permutations(temp_shop_seq):
                        temp_dlv_seq = list(perm)
                        simulated_time = current_bundle[0].ready_time
                        feasible = True
                        for i in range(len(temp_dlv_seq)):
                            if i == 0:
                                simulated_time += rider.T[first_order.id, temp_dlv_seq[i]] + rider.T[temp_dlv_seq[i], first_order.id + K]
                            else:
                                simulated_time += rider.T[temp_dlv_seq[i - 1] + K, temp_dlv_seq[i] + K]
                            if simulated_time > all_orders[temp_dlv_seq[i]].deadline:
                                feasible = False
                                break
                        if feasible:
                            break

                    if feasible:
                        min_distance = total_distance
                        next_order = order

            if next_order is None:
                break

            # 번들에 새로운 주문 추가
            current_bundle.append(next_order)
            current_volume += next_order.volume
            current_time += rider.T[current_bundle[-2].id, next_order.id]
            remaining_orders.remove(next_order)

            # 번들의 모든 주문이 마감 시간 내에 배달 가능한지 확인
            feasible = True
            simulated_time = current_bundle[0].ready_time
            for i in range(len(current_bundle)):
                if i == 0:
                    simulated_time += rider.T[first_order.id, current_bundle[i].id] + rider.T[current_bundle[i].id, first_order.id + K]
                else:
                    simulated_time += rider.T[current_bundle[i-1].id, current_bundle[i].id] + rider.T[current_bundle[i].id, current_bundle[i-1].id + K]

                if simulated_time > current_bundle[i].deadline:
                    feasible = False
                    break

            if not feasible:
                current_bundle.pop()
                remaining_orders.insert(0, next_order)
                break

        shop_seq = [order.id for order in current_bundle]

        best_dlv_seq = None
        min_total_dist = float('inf')
        for perm in permutations(shop_seq):
            dlv_seq = list(perm)
            total_dist = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
            if total_dist < min_total_dist:
                feasible = True
                current_time = current_bundle[0].ready_time
                for i in range(len(dlv_seq)):
                    if i == 0:
                        current_time += rider.T[shop_seq[-1], dlv_seq[i] + K]
                    else:
                        current_time += rider.T[dlv_seq[i - 1] + K, dlv_seq[i] + K]
                    if current_time > all_orders[dlv_seq[i]].deadline:
                        feasible = False
                        break
                if feasible:
                    min_total_dist = total_dist
                    best_dlv_seq = dlv_seq

        if best_dlv_seq is None:
            continue

        new_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, min_total_dist)
        bundles.append(new_bundle)
        rider.available_number -= 1

    return bundles, remaining_orders

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # 주문들을 ready_time 기준으로 정렬
    sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)

    # A solution is a list of bundles
    solution = []

    # 라이더를 유형별로 나눔
    bike_riders = [r for r in all_riders if r.type == 'BIKE']
    car_riders = [r for r in all_riders if r.type == 'CAR']
    walk_riders = [r for r in all_riders if r.type == 'WALK']

    all_bundles = []

    # BIKE 라이더에게 우선 할당
    for bike_rider in bike_riders:
        bundles, sorted_orders = assign_orders_to_rider(bike_rider, sorted_orders, dist_mat, K, all_orders)
        all_bundles.extend(bundles)

    # 남은 주문들을 CAR 또는 WALK 라이더에게 할당
    remaining_riders = car_riders + walk_riders
    random.shuffle(remaining_riders)
    while sorted_orders and remaining_riders:
        rider = remaining_riders.pop(0)
        bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
        all_bundles.extend(bundles)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')

    while time.time() - start_time < timelimit:
        iter = 0
        max_merge_iter = 1000

        while iter < max_merge_iter and time.time() - start_time < timelimit:
            bundle1, bundle2 = select_two_bundles(all_bundles)
            new_bundle = try_merging_bundles(K, dist_mat, all_orders, bundle1, bundle2)

            if new_bundle is not None:
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
            if new_rider is not None:
                old_rider = bundle.rider
                if try_bundle_rider_changing(all_orders, dist_mat, bundle, new_rider):
                    old_rider.available_number += 1
                    new_rider.available_number -= 1

        cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
        if cur_obj < best_obj:
            best_obj = cur_obj
            print(f'New best obj after rider reassignment = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution
