from util import *

def calculate_regret(bundle, current_rider, alternative_riders, all_orders, dist_mat, K):
    current_cost = get_total_distance(K, dist_mat, bundle.shop_seq, bundle.dlv_seq) * current_rider.var_cost + current_rider.fixed_cost
    regrets = []
    for alt_rider in alternative_riders:
        alt_cost = get_total_distance(K, dist_mat, bundle.shop_seq, bundle.dlv_seq) * alt_rider.var_cost + alt_rider.fixed_cost
        regrets.append((alt_rider, alt_cost - current_cost))
    
    best_rider, min_regret = min(regrets, key=lambda x: x[1])
    return best_rider, min_regret

def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):

    start_time = time.time()

    for r in all_riders:
        r.T = np.round(dist_mat/r.speed + r.service_time)

    solution = []

    car_rider = None
    for r in all_riders:
        if r.type == 'CAR':
            car_rider = r

    all_bundles = []

    for ord in all_orders:
        new_bundle = Bundle(all_orders, car_rider, [ord.id], [ord.id], ord.volume, dist_mat[ord.id, ord.id+K])
        all_bundles.append(new_bundle)
        car_rider.available_number -= 1

    best_obj = sum((bundle.cost for bundle in all_bundles)) / K
    print(f'Best obj = {best_obj}')

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
            # Regret algorithm applied here
            alternative_riders = [r for r in all_riders if r.available_number > 0 and r != bundle.rider]
            if alternative_riders:
                best_rider, min_regret = calculate_regret(bundle, bundle.rider, alternative_riders, all_orders, dist_mat, K)
                if min_regret < 0:
                    old_rider = bundle.rider
                    if try_bundle_rider_changing(all_orders, dist_mat, bundle, best_rider):
                        old_rider.available_number += 1
                        best_rider.available_number -= 1

                if time.time() - start_time > timelimit:
                    break

        cur_obj = sum((bundle.cost for bundle in all_bundles)) / K
        if cur_obj < best_obj:
            best_obj = cur_obj
            print(f'Best obj = {best_obj}')

    solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in all_bundles
    ]

    return solution
