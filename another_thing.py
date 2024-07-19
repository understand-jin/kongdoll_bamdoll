# import numpy as np
# import time
# import random
# from itertools import permutations
# from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

# def find_nearest_orders(first_order, remaining_orders, dist_mat, K, num_orders=10):
#     distances = [(order, dist_mat[first_order.id, order.id] + dist_mat[first_order.id + K, order.id + K]) for order in remaining_orders]
#     distances.sort(key=lambda x: x[1])
#     nearest_orders = [order for order, dist in distances[:num_orders]]
#     return nearest_orders


# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         print(f"Remaining orders before assignment: {[order.id for order in remaining_orders]}")
#         current_order = remaining_orders.pop(0)
#         current_bundle = [current_order]
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         first_order = current_order  # 첫 번째 주문을 저장

#         nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)

#         for next_order in nearest_orders:
#             if current_volume + next_order.volume > rider.capa:
#                 continue
            
#             # 현재 번들 및 새로운 주문을 번들로 만들어 배달 순서 정렬
#             current_bundle_ids = [o.id for o in current_bundle]
#             next_bundle_ids = [next_order.id]

#             combined_shop_seq = current_bundle_ids + next_bundle_ids
#             combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

#             # 새로운 번들 생성
#             new_bundle = Bundle(all_orders, rider, combined_shop_seq, combined_delivery_seq, current_volume + next_order.volume, 0)
#             new_bundle.total_dist = get_total_distance(K, dist_mat, combined_shop_seq, combined_delivery_seq)
#             new_bundle.update_cost()

#             # 새로운 번들을 병합 테스트
#             is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
#             merged_bundle = None
#             if is_feasible == 0 :
#                 merged_bundle = try_merging_bundles(K, dist_mat, all_orders, Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

#             if merged_bundle is not None:
#                 current_bundle.append(next_order)
#                 current_volume += next_order.volume
#                 current_time += rider.T[current_bundle[-2].id, next_order.id]
#                 remaining_orders.remove(next_order)
#                 print(f"Remaining orders before assignment: {[order.id for order in remaining_orders]}")
#                 break  # 번들에 추가하면 다음 주문으로 이동

#         shop_seq = [order.id for order in current_bundle]

#         # 배달 순서를 마감시간 기준으로 정렬
#         delivery_seq = shop_seq[:]  # 초기 배달 순서는 픽업 순서와 동일
#         delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
#         best_dlv_seq = delivery_seq

#         # 최종 번들 생성
#         final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
#         bundles.append(final_bundle)
#         print(f"Remaining orders before assignment: {[order.id for order in remaining_orders]}")
#         rider.available_number -= 1

#     return bundles, remaining_orders


# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
#     start_time = time.time()

#     for r in all_riders:
#         r.T = np.round(dist_mat / r.speed + r.service_time)

#     # 주문들을 ready_time 기준으로 정렬
#     sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)

#     # A solution is a list of bundles
#     solution = []

#     # 라이더를 유형별로 나눔
#     bike_riders = [r for r in all_riders if r.type == 'BIKE']
#     car_riders = [r for r in all_riders if r.type == 'CAR']
#     walk_riders = [r for r in all_riders if r.type == 'WALK']

#     all_bundles = []

#     # BIKE 라이더에게 우선 할당
#     for bike_rider in bike_riders:
#         if not sorted_orders:
#             break
#         if bike_rider.available_number > 0:
#             bundles, sorted_orders = assign_orders_to_rider(bike_rider, sorted_orders, dist_mat, K, all_orders)
#             for bundle in bundles:
#                 if test_route_feasibility(all_orders, bike_rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                     all_bundles.append(bundle)

#     # 남은 주문들을 CAR 또는 WALK 라이더에게 할당
#     remaining_riders = car_riders + walk_riders
#     random.shuffle(remaining_riders)
#     while sorted_orders and remaining_riders:
#         rider = remaining_riders.pop(0)
#         if rider.available_number > 0:
#             bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
#             for bundle in bundles:
#                 if test_route_feasibility(all_orders, rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                     all_bundles.append(bundle)

#     # 모든 주문이 할당되었는지 확인하고, 할당되지 않은 주문들을 다른 라이더에게 할당 시도
#     unassigned_orders = sorted_orders[:]
#     for order in unassigned_orders:
#         assigned = False
#         for rider in all_riders:
#             if rider.available_number > 0:
#                 bundles, _ = assign_orders_to_rider(rider, [order], dist_mat, K, all_orders)
#                 if bundles:
#                     for bundle in bundles:
#                         if test_route_feasibility(all_orders, rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                             all_bundles.append(bundle)
#                             assigned = True
#                             break
#                 if assigned:
#                     break
#         if not assigned:
#             # 모든 라이더가 사용 중일 경우 car 라이더 중 하나를 선택하여 할당
#             car_rider = random.choice(car_riders)
#             bundles, _ = assign_orders_to_rider(car_rider, [order], dist_mat, K, all_orders)
#             for bundle in bundles:
#                 if test_route_feasibility(all_orders, car_rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                     all_bundles.append(bundle)
#             car_rider.available_number -= 1

#     best_obj = sum((bundle.cost for bundle in all_bundles)) / K
#     print(f'Initial best obj = {best_obj}')

#     while time.time() - start_time < timelimit:
#         iter = 0
#         max_merge_iter = 1000

#         while iter < max_merge_iter and time.time() - start_time < timelimit:
#             bundle1, bundle2 = select_two_bundles(all_bundles)
#             new_bundle = try_merging_bundles(K, dist_mat, all_orders, bundle1, bundle2)
#             if new_bundle is not None:
#                 is_feasible = test_route_feasibility(all_orders, new_bundle.rider, new_bundle.shop_seq, new_bundle.dlv_seq)
#                 if is_feasible == 0:
#                     all_bundles.remove(bundle1)
#                     bundle1.rider.available_number += 1

#                     all_bundles.remove(bundle2)
#                     bundle2.rider.available_number += 1

#                     all_bundles.append(new_bundle)
#                     new_bundle.rider.available_number -= 1

#                     cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
#                     if cur_obj < best_obj:
#                         best_obj = cur_obj
#                         print(f'New best obj after merge = {best_obj}')
#             else:
#                 iter += 1

#         for bundle in all_bundles:
#             new_rider = get_cheaper_available_riders(all_riders, bundle.rider)
#             if new_rider is not None and new_rider.available_number > 0:
#                 old_rider = bundle.rider
#                 temp_bundle = bundle  # Copy the bundle for testing
#                 if try_bundle_rider_changing(all_orders, dist_mat, temp_bundle, new_rider):
#                     is_feasible = test_route_feasibility(all_orders, new_rider, temp_bundle.shop_seq, temp_bundle.dlv_seq)
#                     if is_feasible == 0:
#                         old_rider.available_number += 1
#                         new_rider.available_number -= 1
#                         bundle.rider = new_rider
#                         bundle.shop_seq = temp_bundle.shop_seq
#                         bundle.dlv_seq = temp_bundle.dlv_seq
#                         bundle.update_cost()

#         cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
#         if cur_obj < best_obj:
#             best_obj = cur_obj
#             print(f'New best obj after rider reassignment = {best_obj}')

#     solution = [
#         [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
#         for bundle in all_bundles
#     ]

#     return solution

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

def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, solution):
    bundles = []
    remaining_orders = orders[:]
    
    while remaining_orders and rider.available_number > 0:
        current_order = remaining_orders.pop(0)
        print(f"Assigning order {current_order.id} to rider {rider.type}")
        current_bundle = [current_order]
        current_volume = current_order.volume
        current_time = current_order.ready_time

        first_order = current_order

        nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)
        
        while True:
            added_to_bundle = False

            for next_order in nearest_orders:
                if next_order not in remaining_orders:
                    continue

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
                    merged_bundle = try_merging_bundles(K, dist_mat, all_orders, 
                        Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), 
                        Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

                if merged_bundle is not None:
                    current_bundle.append(next_order)
                    current_volume += next_order.volume
                    current_time += rider.T[current_bundle[-2].id, next_order.id]
                    remaining_orders.remove(next_order)
                    print(f"Added order {next_order.id} to bundle for rider {rider.type}")
                    added_to_bundle = True
                    break

            if not added_to_bundle:
                break

        shop_seq = [order.id for order in current_bundle]

        delivery_seq = shop_seq[:]
        delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
        best_dlv_seq = delivery_seq

        final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
        print(f"Created bundle for rider {rider.type}: shop_seq = {shop_seq}, delivery_seq = {delivery_seq}")
        bundles.append(final_bundle)

        # Ensure the solution is updated here
        solution.append([rider.type, shop_seq, best_dlv_seq])

        rider.available_number -= 1

    print(f"Remaining orders after assigning to rider {rider.type}: {[order.id for order in remaining_orders]}")
    return bundles, remaining_orders

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)
    print(f"Initial sorted orders: {[order.id for order in sorted_orders]}")

    solution = []

    bike_riders = [r for r in all_riders if r.type == 'BIKE']
    car_riders = [r for r in all_riders if r.type == 'CAR']
    walk_riders = [r for r in all_riders if r.type == 'WALK']

    all_bundles = []
    remaining_orders = sorted_orders[:]

    for bike_rider in bike_riders:
        if not remaining_orders:
            break
        if bike_rider.available_number > 0:
            bundles, remaining_orders = assign_orders_to_rider(bike_rider, remaining_orders, dist_mat, K, all_orders, solution)
            for bundle in bundles:
                #if test_route_feasibility(all_orders, bike_rider, bundle.shop_seq, bundle.dlv_seq) == 0:
                    all_bundles.append(bundle)
                    print(f"Added bundle to solution: rider = {bike_rider.type}, shop_seq = {bundle.shop_seq}, dlv_seq = {bundle.dlv_seq}")

    remaining_riders = car_riders + walk_riders
    random.shuffle(remaining_riders)
    while remaining_orders and remaining_riders:
        rider = remaining_riders.pop(0)
        if rider.available_number > 0:
            bundles, remaining_orders = assign_orders_to_rider(rider, remaining_orders, dist_mat, K, all_orders, solution)
            for bundle in bundles:
                #if test_route_feasibility(all_orders, rider, bundle.shop_seq, bundle.dlv_seq) == 0:
                    all_bundles.append(bundle)
                    print(f"Added bundle to solution: rider = {rider.type}, shop_seq = {bundle.shop_seq}, dlv_seq = {bundle.dlv_seq}")

    if remaining_orders:
        print(f"남은 주문이 있습니다: {[order.id for order in remaining_orders]}")
        raise Exception("모든 주문이 할당되지 않았습니다!")
    else:
        print("모든 주문이 성공적으로 할당되었습니다.")

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
                    print(f"Merging bundles {bundle1.shop_seq} and {bundle2.shop_seq}")
                    all_bundles.remove(bundle1)
                    bundle1.rider.available_number += 1

                    all_bundles.remove(bundle2)
                    bundle2.rider.available_number += 1

                    all_bundles.append(new_bundle)
                    solution.append([new_bundle.rider.type, new_bundle.shop_seq, new_bundle.dlv_seq])
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

                        solution.append([new_rider.type, bundle.shop_seq, bundle.dlv_seq])
                        print(f'Changed rider of bundle with shop_seq {bundle.shop_seq} from {old_rider.type} to {new_rider.type}')

        cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
        if cur_obj < best_obj:
            best_obj = cur_obj
            print(f'New best obj after rider reassignment = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution






# import numpy as np
# import time
# import random
# from itertools import permutations
# from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

# def find_nearest_orders(first_order, remaining_orders, dist_mat, K, num_orders=10):
#     distances = [(order, dist_mat[first_order.id, order.id] + dist_mat[first_order.id + K, order.id + K]) for order in remaining_orders]
#     distances.sort(key=lambda x: x[1])
#     nearest_orders = [order for order, dist in distances[:num_orders]]
#     return nearest_orders

# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         current_order = remaining_orders.pop(0)  # remaining_orders에서 첫 번째 주문을 꺼내와 current_order에 할당하고 제거
#         current_bundle = [current_order]
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         first_order = current_order  # 첫 번째 주문을 저장

#         nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)
        
#         while True:  # 주문을 추가할 수 있는지 계속 확인하기 위한 루프
#             added_to_bundle = False

#             for next_order in nearest_orders:
#                 if next_order not in remaining_orders:
#                     continue  # 이미 번들에 추가된 주문은 건너뜀

#                 if current_volume + next_order.volume > rider.capa:
#                     continue
                
#                 # 현재 번들 및 새로운 주문을 번들로 만들어 배달 순서 정렬
#                 current_bundle_ids = [o.id for o in current_bundle]
#                 next_bundle_ids = [next_order.id]

#                 combined_shop_seq = current_bundle_ids + next_bundle_ids
#                 combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

#                 # 새로운 번들 생성
#                 new_bundle = Bundle(all_orders, rider, combined_shop_seq, combined_delivery_seq, current_volume + next_order.volume, 0)
#                 new_bundle.total_dist = get_total_distance(K, dist_mat, combined_shop_seq, combined_delivery_seq)
#                 new_bundle.update_cost()

#                 # 새로운 번들을 병합 테스트
#                 is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
#                 merged_bundle = None
#                 if is_feasible == 0:
#                     merged_bundle = try_merging_bundles(K, dist_mat, all_orders, Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

#                 if merged_bundle is not None:
#                     current_bundle.append(next_order)
#                     current_volume += next_order.volume
#                     current_time += rider.T[current_bundle[-2].id, next_order.id]
#                     remaining_orders.remove(next_order)
#                     added_to_bundle = True
#                     break  # 번들에 추가하면 다음 주문으로 이동

#             if not added_to_bundle:
#                 break  # 더 이상 추가할 주문이 없으면 루프 종료

#         shop_seq = [order.id for order in current_bundle]

#         # 배달 순서를 마감시간 기준으로 정렬
#         delivery_seq = shop_seq[:]  # 초기 배달 순서는 픽업 순서와 동일
#         delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
#         best_dlv_seq = delivery_seq

#         # 최종 번들 생성
#         final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
#         bundles.append(final_bundle)
#         rider.available_number -= 1

#     return bundles, remaining_orders




# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
#     start_time = time.time()

#     for r in all_riders:
#         r.T = np.round(dist_mat / r.speed + r.service_time)

#     # 주문들을 ready_time 기준으로 정렬
#     sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)
#     #print(sorted_orders)

#     # A solution is a list of bundles
#     solution = []

#     # 라이더를 유형별로 나눔
#     bike_riders = [r for r in all_riders if r.type == 'BIKE']
#     car_riders = [r for r in all_riders if r.type == 'CAR']
#     walk_riders = [r for r in all_riders if r.type == 'WALK']

#     all_bundles = []

#     # BIKE 라이더에게 우선 할당
#     for bike_rider in bike_riders:
#         if not sorted_orders:
#             break
#         if bike_rider.available_number > 0:
#             bundles, sorted_orders = assign_orders_to_rider(bike_rider, sorted_orders, dist_mat, K, all_orders)
#             for bundle in bundles:
#                 if test_route_feasibility(all_orders, bike_rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                     all_bundles.append(bundle)

#     # 남은 주문들을 CAR 또는 WALK 라이더에게 할당
#     remaining_riders = car_riders + walk_riders
#     random.shuffle(remaining_riders)
#     while sorted_orders and remaining_riders:
#         rider = remaining_riders.pop(0)
#         if rider.available_number > 0:
#             bundles, sorted_orders = assign_orders_to_rider(rider, sorted_orders, dist_mat, K, all_orders)
#             for bundle in bundles:
#                 if test_route_feasibility(all_orders, rider, bundle.shop_seq, bundle.dlv_seq) == 0:
#                     all_bundles.append(bundle)
                    
#     if sorted_orders:
#         print(f"남은 주문이 있습니다: {sorted_orders}")
#         raise Exception("모든 주문이 할당되지 않았습니다!")
    
#     best_obj = sum((bundle.cost for bundle in all_bundles)) / K
#     print(f'Initial best obj = {best_obj}')

#     while time.time() - start_time < timelimit:
#         iter = 0
#         max_merge_iter = 1000

#         while iter < max_merge_iter and time.time() - start_time < timelimit:
#             bundle1, bundle2 = select_two_bundles(all_bundles)
#             new_bundle = try_merging_bundles(K, dist_mat, all_orders, bundle1, bundle2)
#             if new_bundle is not None:
#                 is_feasible = test_route_feasibility(all_orders, new_bundle.rider, new_bundle.shop_seq, new_bundle.dlv_seq)
#                 if is_feasible == 0:
#                     all_bundles.remove(bundle1)
#                     bundle1.rider.available_number += 1

#                     all_bundles.remove(bundle2)
#                     bundle2.rider.available_number += 1

#                     all_bundles.append(new_bundle)
#                     new_bundle.rider.available_number -= 1

#                     #print(f'Merged bundle1 with shop_seq {bundle1.shop_seq} and bundle2 with shop_seq {bundle2.shop_seq} into new bundle with shop_seq {new_bundle.shop_seq}')

#                     cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
#                     if cur_obj < best_obj:
#                         best_obj = cur_obj
#                         print(f'New best obj after merge = {best_obj}')
#             else:
#                 iter += 1

#         for bundle in all_bundles:
#             new_rider = get_cheaper_available_riders(all_riders, bundle.rider)
#             if new_rider is not None and new_rider.available_number > 0:
#                 old_rider = bundle.rider
#                 temp_bundle = bundle  # Copy the bundle for testing
#                 if try_bundle_rider_changing(all_orders, dist_mat, temp_bundle, new_rider):
#                     is_feasible = test_route_feasibility(all_orders, new_rider, temp_bundle.shop_seq, temp_bundle.dlv_seq)
#                     if is_feasible == 0:
#                         old_rider.available_number += 1
#                         new_rider.available_number -= 1
#                         bundle.rider = new_rider
#                         bundle.shop_seq = temp_bundle.shop_seq
#                         bundle.dlv_seq = temp_bundle.dlv_seq
#                         bundle.update_cost()

#                         #print(f'Changed rider of bundle with shop_seq {bundle.shop_seq} from {old_rider.type} to {new_rider.type}')


#         cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
#         if cur_obj < best_obj:
#             best_obj = cur_obj
#             print(f'New best obj after rider reassignment = {best_obj}')

#     solution = [
#         [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
#         for bundle in all_bundles
#     ]

#     return solution


