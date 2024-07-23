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

# def assign_orders_to_rider(rider, orders, dist_mat, K, all_orders, solution):
#     bundles = []
#     remaining_orders = orders[:]
    
#     while remaining_orders and rider.available_number > 0:
#         current_order = remaining_orders.pop(0)
#         #print(f"Assigning order {current_order.id} to rider {rider.type}")
#         current_bundle = [current_order]
#         current_volume = current_order.volume
#         current_time = current_order.ready_time

#         first_order = current_order

#         nearest_orders = find_nearest_orders(first_order, remaining_orders, dist_mat, K, 50)
        
#         while True:
#             added_to_bundle = False

#             for next_order in nearest_orders:
#                 if next_order not in remaining_orders:
#                     continue

#                 if current_volume + next_order.volume > rider.capa:
#                     continue
                
#                 current_bundle_ids = [o.id for o in current_bundle]
#                 next_bundle_ids = [next_order.id]

#                 combined_shop_seq = current_bundle_ids + next_bundle_ids
#                 combined_delivery_seq = sorted(combined_shop_seq, key=lambda order_id: all_orders[order_id].deadline)

#                 new_bundle = Bundle(all_orders, rider, combined_shop_seq, combined_delivery_seq, current_volume + next_order.volume, 0)
#                 new_bundle.total_dist = get_total_distance(K, dist_mat, combined_shop_seq, combined_delivery_seq)
#                 new_bundle.update_cost()

#                 is_feasible = test_route_feasibility(all_orders, rider, combined_shop_seq, combined_delivery_seq)
#                 merged_bundle = None
#                 if is_feasible == 0:
#                     merged_bundle = try_merging_bundles(K, dist_mat, all_orders, 
#                         Bundle(all_orders, rider, current_bundle_ids, current_bundle_ids, current_volume, 0), 
#                         Bundle(all_orders, rider, next_bundle_ids, next_bundle_ids, next_order.volume, 0))

#                 if merged_bundle is not None:
#                     current_bundle.append(next_order)
#                     current_volume += next_order.volume
#                     current_time += rider.T[current_bundle[-2].id, next_order.id]
#                     remaining_orders.remove(next_order)
#                     #print(f"Added order {next_order.id} to bundle for rider {rider.type}")
#                     added_to_bundle = True
#                     break

#             if not added_to_bundle:
#                 break

#         shop_seq = [order.id for order in current_bundle]

#         delivery_seq = shop_seq[:]
#         delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
#         best_dlv_seq = delivery_seq

#         final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
#         #print(f"Created bundle for rider {rider.type}: shop_seq = {shop_seq}, delivery_seq = {delivery_seq}")
#         bundles.append(final_bundle)

#         # Ensure the solution is updated here
#         solution.append([rider.type, shop_seq, best_dlv_seq])

#         rider.available_number -= 1

#     #print(f"Remaining orders after assigning to rider {rider.type}: {[order.id for order in remaining_orders]}")
#     return bundles, remaining_orders

# def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
#     start_time = time.time()

#     for r in all_riders:
#         r.T = np.round(dist_mat / r.speed + r.service_time)

#     sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)
#     #print(f"Initial sorted orders: {[order.id for order in sorted_orders]}")

#     solution = []

#     bike_riders = [r for r in all_riders if r.type == 'BIKE']
#     car_riders = [r for r in all_riders if r.type == 'CAR']
#     walk_riders = [r for r in all_riders if r.type == 'WALK']

#     all_bundles = []
#     remaining_orders = sorted_orders[:]

#     for bike_rider in bike_riders:
#         if not remaining_orders:
#             break
#         if bike_rider.available_number > 0:
#             bundles, remaining_orders = assign_orders_to_rider(bike_rider, remaining_orders, dist_mat, K, all_orders, solution)
#             for bundle in bundles:
#                 all_bundles.append(bundle)
#                 #print(f"Added bundle to solution: rider = {bike_rider.type}, shop_seq = {bundle.shop_seq}, dlv_seq = {bundle.dlv_seq}")

#     remaining_riders = car_riders + walk_riders
#     random.shuffle(remaining_riders)
#     while remaining_orders and remaining_riders:
#         rider = remaining_riders.pop(0)
#         if rider.available_number > 0:
#             bundles, remaining_orders = assign_orders_to_rider(rider, remaining_orders, dist_mat, K, all_orders, solution)
#             for bundle in bundles:
#                 all_bundles.append(bundle)
#                 #print(f"Added bundle to solution: rider = {rider.type}, shop_seq = {bundle.shop_seq}, dlv_seq = {bundle.dlv_seq}")

    
    

#     best_obj = sum((bundle.cost for bundle in all_bundles)) / K
#     print(f'Initial best obj = {best_obj}')


#     solution = [
#         [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
#         for bundle in all_bundles
#     ]

#     return solution

import numpy as np
import time
import random
from util import Bundle, Order, Rider, solution_check, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing

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
                    added_to_bundle = True
                    break

            if not added_to_bundle:
                break

        shop_seq = [order.id for order in current_bundle]

        delivery_seq = shop_seq[:]
        delivery_seq.sort(key=lambda order_id: all_orders[order_id].deadline)
        best_dlv_seq = delivery_seq

        final_bundle = Bundle(all_orders, rider, shop_seq, best_dlv_seq, current_volume, get_total_distance(K, dist_mat, shop_seq, best_dlv_seq))
        bundles.append(final_bundle)

        solution.append([rider.type, shop_seq, best_dlv_seq])

        rider.available_number -= 1

    return bundles, remaining_orders

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    sorted_orders = sorted(all_orders, key=lambda order: order.ready_time)

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
                all_bundles.append(bundle)

    remaining_riders = car_riders + walk_riders
    random.shuffle(remaining_riders)
    while remaining_orders and remaining_riders:
        rider = remaining_riders.pop(0)
        if rider.available_number > 0:
            bundles, remaining_orders = assign_orders_to_rider(rider, remaining_orders, dist_mat, K, all_orders, solution)
            for bundle in bundles:
                all_bundles.append(bundle)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Initial best obj = {best_obj}')


    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution

def is_feasible(solution, K, all_orders, all_riders, dist_mat):
    checked_solution = solution_check(K, all_orders, all_riders, dist_mat, solution)
    return checked_solution['feasible']