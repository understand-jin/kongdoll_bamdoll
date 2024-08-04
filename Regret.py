import numpy as np
import time
import itertools
import random
from itertools import permutations
from util import Bundle, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
import concurrent.futures

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

def cluster_orders(K, dist_mat, all_orders, cluster_size):
    unassigned_orders = list(range(K))
    clusters = []

    while len(unassigned_orders) > 0:
        current_order = unassigned_orders.pop(0)
        current_bundle = [all_orders[current_order]]
        
        # 가까운 주문들로 클러스터 생성
        nearest_orders = find_nearest_orders(current_bundle, [all_orders[i] for i in unassigned_orders], dist_mat, K, cluster_size - 1)
        cluster = [current_order] + [order.id for order in nearest_orders]
        
        clusters.append(cluster)
        
        # 클러스터링된 주문들을 unassigned_orders에서 제거
        unassigned_orders = [order for order in unassigned_orders if order not in cluster]
        
    return clusters

def regret_order_clustering_with_preclustering(K, dist_mat, all_orders, all_riders, cluster_size, max_permutations=50):
    # 차량(Car) 배달원 리스트 생성
    car_riders = [r for r in all_riders if r.type == 'CAR']
    
    # 주문을 클러스터링
    clusters = cluster_orders(K, dist_mat, all_orders, cluster_size)

    bundles = []
    assigned_orders = set()  # 이미 번들에 할당된 주문을 추적하기 위해 사용

    for cluster in clusters:
        unassigned_orders = set(cluster) - assigned_orders  # 이미 할당된 주문은 제외
        
        while unassigned_orders:
            best_cluster = None
            best_regret_value = float('-inf')

            # 가능한 모든 주문 묶음 조합을 생성
            for bundle_size in range(2, min(6, len(unassigned_orders) + 1)):  # 작은 크기의 묶음부터 탐색
                for cluster_subset in itertools.combinations(unassigned_orders, bundle_size):
                    best_cost = float('inf')
                    second_best_cost = float('inf')
                    best_rider = None

                    # 각 묶음에 대해 최선과 두 번째로 좋은 비용 계산
                    for rider in car_riders:
                        # 차량(Car) 배달원의 용량을 기준으로 묶음 가능 여부 확인
                        if sum(all_orders[i].volume for i in cluster_subset) <= rider.capa:
                            permuted_sequences = itertools.islice(itertools.permutations(cluster_subset), max_permutations)
                            for shop_seq in permuted_sequences:
                                for dlv_seq in itertools.permutations(shop_seq):
                                    if test_route_feasibility(all_orders, rider, shop_seq, dlv_seq) == 0:
                                        total_distance = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
                                        total_cost = rider.fixed_cost + (total_distance / 100.0) * rider.var_cost
                                        avg_cost = total_cost / len(cluster_subset)
                                        if avg_cost < best_cost:
                                            second_best_cost = best_cost
                                            best_cost = avg_cost
                                            best_rider = rider
                                        elif avg_cost < second_best_cost:
                                            second_best_cost = avg_cost

                    # Regret 값 계산
                    regret_value = second_best_cost - best_cost
                    if regret_value > best_regret_value and best_rider is not None:
                        best_regret_value = regret_value
                        best_cluster = (cluster_subset, best_rider, best_cost, shop_seq, dlv_seq)

            if best_cluster:
                cluster_subset, rider, cost, shop_seq, dlv_seq = best_cluster
                total_volume = sum(all_orders[i].volume for i in cluster_subset)
                total_dist = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
                bundles.append(Bundle(all_orders, rider, list(shop_seq), list(dlv_seq), total_volume, total_dist))
                unassigned_orders -= set(cluster_subset)
                assigned_orders.update(cluster_subset)  # 이미 할당된 주문을 기록
                rider.available_number -= 1
            else:
                # 어떤 주문도 묶이지 않을 경우, 첫 번째 주문을 단독으로 묶음으로 만들어 추가
                order_id = unassigned_orders.pop()
                bundles.append(Bundle(all_orders, car_riders[0], [order_id], [order_id], all_orders[order_id].volume, 0))
                assigned_orders.add(order_id)

    # 모든 주문이 할당되었는지 확인
    if len(assigned_orders) != K:
        raise ValueError(f"Some orders were not assigned to any bundle: {set(range(K)) - assigned_orders}")

    # 평균 비용 계산 및 출력
    total_cost = sum(bundle.rider.fixed_cost + (bundle.total_dist / 100.0) * bundle.rider.var_cost for bundle in bundles)
    avg_cost = total_cost / len(bundles)
    print(f'Average cost per bundle: {avg_cost}')

    return bundles





def algorithm(K, all_orders, all_riders, dist_mat, timelimit=60):
    # Run single instance of the algorithm
    solution, best_obj = regret_order_clustering_with_preclustering(K, dist_mat, all_orders, all_riders, cluster_size=10, max_permutations=50)

    final_solution = [
        [bundle.rider.type, bundle.shop_seq, bundle.dlv_seq]
        for bundle in solution
    ]
    
    # Print the best objective value found
    print(f'Best objective value: {best_obj}')

    return final_solution


