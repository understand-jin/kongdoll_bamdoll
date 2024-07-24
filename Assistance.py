import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, Rider, Order, get_avg_cost, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm
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

