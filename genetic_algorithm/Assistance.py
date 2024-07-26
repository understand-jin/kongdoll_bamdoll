import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, Rider, Order, get_avg_cost, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm, assign_orders_to_rider
#from after_crossover import assign_orders_to_rider
#from myalgorithm import algorithm

def initialize_population(K, all_orders, all_riders, dist_mat, population_size=50, timelimit=60):
    population = []
    for i in range(50):
        try:
            # 매 반복마다 새로운 라이더와 주문 리스트를 초기화해야 함
            new_riders = [Rider([r.type, r.speed, r.capa, r.var_cost, r.fixed_cost, r.service_time, r.available_number]) for r in all_riders]
            new_orders = [Order([o.id, o.order_time, o.shop_lat, o.shop_lon, o.dlv_lat, o.dlv_lon, o.cook_time, o.volume, o.deadline]) for o in all_orders]
            solution = algorithm(K, new_orders, new_riders, dist_mat, timelimit)
            if solution:
                population.append(solution)
            else:
                pass
        except Exception as e:
            print(f"Exception during solution generation {i}: {e}")
    return population

def fitness(solution, K, all_orders, all_riders, dist_mat):
    # solution_check 함수를 사용하여 주어진 solution의 타당성 검사
    checked_solution = solution_check(K, all_orders, all_riders, dist_mat, solution)

    # Solution이 유효한 경우 평균 비용을 반환
    if checked_solution['feasible']:
        print(f"fitness : {checked_solution['avg_cost']}")
        return checked_solution['avg_cost']
    else:
        # Solution이 유효하지 않은 경우 매우 큰 값을 반환하여 선택되지 않도록 함
        return float('inf')
    
def select_population(population, population_fitness, num_selections):
    #1. 적합도 값이 무한대가 아닌 해 들의 역수의 합을 계산함
    total_fitness = sum(1 / f for f in population_fitness if f != float('inf')) 
    #2. 각 해의 선택 확률을 계산함
    selection_probs = [(1 / f) / total_fitness if f != float('inf') else 0 for f in population_fitness]
    #3. 주어진 확률에 따라 해를 선택함
    selected_population = random.choices(population, weights=selection_probs, k=num_selections)
    return selected_population

def crossover(parent1, parent2, K, all_orders, dist_mat, all_riders):
    # 부모1로부터 특정 부분 복사하여 child1 생성
    cxpoint1, cxpoint2 = sorted(random.sample(range(len(parent1)), 2))
    child1 = parent1[cxpoint1:cxpoint2]
    print(f"after copy parents 1 : {child1}")

    # child1에 포함된 주문을 전체 주문에서 제거하여 remaining_order 정의
    copied_order_ids = set()
    for bundle in child1:
        copied_order_ids.update(bundle[1])  # shop_seq
        copied_order_ids.update(bundle[2])  # dlv_seq

    remaining_orders = [order for order in all_orders if order.id not in copied_order_ids]

    # 부모2에서 remaining_order에 포함된 주문들로 구성된 번들을 child1에 추가
    for bundle in parent2:
        if all(order_id in [order.id for order in remaining_orders] for order_id in bundle[1]) and \
           all(order_id in [order.id for order in remaining_orders] for order_id in bundle[2]):
            child1.append(bundle)
            copied_order_ids.update(bundle[1])
            copied_order_ids.update(bundle[2])
            remaining_orders = [order for order in remaining_orders if order.id not in copied_order_ids]

    print(f"after parents2 : {child1}")

    # remaining_order가 남아있는 경우, first_version_simple.py에서 사용하는 연산으로 처리
    if remaining_orders:
        # 모든 라이더의 가용 가능한 수를 업데이트
        rider_type_count = {}
        for bundle in child1:
            rider_type = bundle[0]
            if rider_type not in rider_type_count:
                rider_type_count[rider_type] = 0
            rider_type_count[rider_type] += 1

        remaining_riders = []
        for rider in all_riders:
            if rider.type in rider_type_count:
                # 가용 가능한 수를 업데이트
                new_available_number = rider.available_number - rider_type_count[rider.type]
                if new_available_number > 0:
                    updated_rider = Rider([rider.type, rider.speed, rider.capa, rider.var_cost, rider.fixed_cost, rider.service_time, new_available_number])
                    remaining_riders.append(updated_rider)
            else:
                remaining_riders.append(rider)
        print("checkl")
        # 라이더를 유형별로 분류
        bike_riders = [r for r in remaining_riders if r.type == 'BIKE']
        car_riders = [r for r in remaining_riders if r.type == 'CAR']
        walk_riders = [r for r in remaining_riders if r.type == 'WALK']

        # 자전거 라이더에게 먼저 할당
        if bike_riders:
            print("check")
            new_bundles, remaining_orders = assign_orders_to_rider(bike_riders, remaining_orders, dist_mat, K, all_orders)
            child1.extend([[bundle.rider.type, bundle.shop_seq, bundle.dlv_seq] for bundle in new_bundles])

        # 남은 주문들을 자동차 및 도보 라이더에게 할당
        if remaining_orders:
            new_bundles, remaining_orders = assign_orders_to_rider(car_riders + walk_riders, remaining_orders, dist_mat, K, all_orders)
            child1.extend([[bundle.rider.type, bundle.shop_seq, bundle.dlv_seq] for bundle in new_bundles])

        print(f"finishing all of the process : {child1}")

        result = solution_check(K, all_orders, all_riders, dist_mat, child1)
        if result['feasible']:
            print("child1 is feasible")
        else:
            print(f"child1 is not feasible: {result['infeasibility']}")

    # 부모2로부터 특정 부분 복사하여 child2 생성
    cxpoint1, cxpoint2 = sorted(random.sample(range(len(parent2)), 2))
    child2 = parent2[cxpoint1:cxpoint2]

    # child2에 포함된 주문을 전체 주문에서 제거하여 remaining_order 정의
    copied_order_ids = set()
    for bundle in child2:
        copied_order_ids.update(bundle[1])  # shop_seq
        copied_order_ids.update(bundle[2])  # dlv_seq

    remaining_orders = [order for order in all_orders if order.id not in copied_order_ids]

    # 부모1에서 remaining_order에 포함된 주문들로 구성된 번들을 child2에 추가
    for bundle in parent1:
        if all(order_id in [order.id for order in remaining_orders] for order_id in bundle[1]) and \
           all(order_id in [order.id for order in remaining_orders] for order_id in bundle[2]):
            child2.append(bundle)
            copied_order_ids.update(bundle[1])
            copied_order_ids.update(bundle[2])
            remaining_orders = [order for order in remaining_orders if order.id not in copied_order_ids]

    # remaining_orders가 남아있는 경우, first_version_simple.py에서 사용하는 연산으로 처리
    if remaining_orders:
        # 모든 라이더의 가용 가능한 수를 업데이트
        rider_type_count = {}
        for bundle in child2:
            rider_type = bundle[0]
            if rider_type not in rider_type_count:
                rider_type_count[rider_type] = 0
            rider_type_count[rider_type] += 1

        remaining_riders = []
        for rider in all_riders:
            if rider.type in rider_type_count:
                # 가용 가능한 수를 업데이트
                new_available_number = rider.available_number - rider_type_count[rider.type]
                if new_available_number > 0:
                    updated_rider = Rider([rider.type, rider.speed, rider.capa, rider.var_cost, rider.fixed_cost, rider.service_time, new_available_number])
                    remaining_riders.append(updated_rider)
            else:
                remaining_riders.append(rider)

        # 라이더를 유형별로 분류
        bike_riders = [r for r in remaining_riders if r.type == 'BIKE']
        car_riders = [r for r in remaining_riders if r.type == 'CAR']
        walk_riders = [r for r in remaining_riders if r.type == 'WALK']

        # 자전거 라이더에게 먼저 할당
        if bike_riders:
            new_bundles, remaining_orders = assign_orders_to_rider(bike_riders, remaining_orders, dist_mat, K, all_orders)
            child2.extend([[bundle.rider.type, bundle.shop_seq, bundle.dlv_seq] for bundle in new_bundles])

        # 남은 주문들을 자동차 및 도보 라이더에게 할당
        if remaining_orders:
            new_bundles, remaining_orders = assign_orders_to_rider(car_riders + walk_riders, remaining_orders, dist_mat, K, all_orders)
            child2.extend([[bundle.rider.type, bundle.shop_seq, bundle.dlv_seq] for bundle in new_bundles])

    # child1과 child2를 반환
    return child1, child2


def is_feasible(solution, K, all_orders, dist_mat):
    for bundle_info in solution:
        rider = bundle_info[0]
        shop_seq = bundle_info[1]
        dlv_seq = bundle_info[2]

        # 경로 유효성 테스트
        if test_route_feasibility(all_orders, rider, shop_seq, dlv_seq) != 0:
            return False
    return True


