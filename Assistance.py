import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, Rider, Order, get_avg_cost, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm

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
                #print(f"Initial solution {i}: {solution}")  # 디버깅 출력
            else:
                print("d")
                #print(f"Initial solution {i} is None or invalid")
        except Exception as e:
            print(f"Exception during solution generation {i}: {e}")
    return population

def fitness(solution, K, all_orders, all_riders, dist_mat):
    try:
        checked_solution = solution_check(K, all_orders, all_riders, dist_mat, solution)
        if checked_solution['feasible']:
            total_cost = 0
            total_orders = len(all_orders)
            
            for bundle_info in solution:
                rider_type = bundle_info[0]
                shop_seq = bundle_info[1]
                dlv_seq = bundle_info[2]
                
                # Get the rider object
                rider = next(r for r in all_riders if r.type == rider_type)
                
                # Calculate the total distance for the bundle
                total_dist = get_total_distance(K, dist_mat, shop_seq, dlv_seq)
                
                # Calculate the cost for this bundle
                bundle_cost = rider.fixed_cost + (total_dist / 100) * rider.var_cost
                total_cost += bundle_cost
                
            avg_cost = total_cost / total_orders
            print(f"Solution fitness (average cost): {avg_cost}")  # 디버깅 출력
            return avg_cost
        else:
            print(f"Solution infeasible: {checked_solution['infeasibility']}")
            return float('inf')
    except Exception as e:
        print(f"Exception in fitness calculation: {e}")
        return float('inf')