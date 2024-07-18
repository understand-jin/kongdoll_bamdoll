from util import *
import numpy as np
import time
import random
from itertools import permutations

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat / r.speed + r.service_time)

    # A solution is a list of bundles
    solution = []

    #------------- Custom algorithm code starts from here --------------#

    bike_riders = [r for r in all_riders if r.type == 'BIKE']
    car_riders = [r for r in all_riders if r.type == 'CAR']
    walk_riders = [r for r in all_riders if r.type == 'WALK']

    all_bundles = []

    for ord in all_orders:
        if bike_riders:
            bike_rider = bike_riders.pop(0)
            new_bundle = Bundle(all_orders, bike_rider, [ord.id], [ord.id], ord.volume, dist_mat[ord.id, ord.id+K])
            all_bundles.append(new_bundle)
            bike_rider.available_number -= 1
            if bike_rider.available_number > 0:
                bike_riders.append(bike_rider)
        elif car_riders:
            car_rider = car_riders.pop(0)
            new_bundle = Bundle(all_orders, car_rider, [ord.id], [ord.id], ord.volume, dist_mat[ord.id, ord.id+K])
            all_bundles.append(new_bundle)
            car_rider.available_number -= 1
            if car_rider.available_number > 0:
                car_riders.append(car_rider)

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Best obj = {best_obj}')

    # Very stupid random merge algorithm
    while True:
        iter = 0
        max_merge_iter = 1000
        
        while iter < max_merge_iter:
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
                    print(f'Best obj = {best_obj}')
            else:
                iter += 1

            if time.time() - start_time > timelimit:
                break

        if time.time() - start_time > timelimit:
            break

        for bundle in all_bundles:
            new_rider = get_cheaper_available_riders(all_riders, bundle.rider)
            if new_rider is not None:
                old_rider = bundle.rider
                if try_bundle_rider_changing(all_orders, dist_mat, bundle, new_rider):
                    old_rider.available_number += 1
                    new_rider.available_number -= 1

                if time.time() - start_time > timelimit:
                    break

        cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
        if cur_obj < best_obj:
            best_obj = cur_obj
            print(f'Best obj = {best_obj}')

    # Solution is a list of bundle information
    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution
