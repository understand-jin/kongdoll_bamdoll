import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, Rider, Order, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm
from Assistance import initialize_population, fitness, select_population


#Genetic_Algorithm
def genetic_algorithm(K, all_orders, all_riders, dist_mat, population_size, generations, crossover_rate=0.8, mutation_rate=0.05, elite_size=2, timelimit=60):
    start_time = time.time()

    # 초기 해 생성
    population = initialize_population(K, all_orders, all_riders, dist_mat, population_size, timelimit)
    
    best_solution = None
    best_fitness = float('inf')

    if time.time() - start_time > timelimit:
        print("Time limit reached.")

        # 적합도 계산
    population_fitness = [fitness(solution, K, all_orders, all_riders, dist_mat) for solution in population]
    
    # 현재 세대에서 최적 해 찾기
    current_best_solution = min(population, key=lambda sol: fitness(sol, K, all_orders, all_riders, dist_mat))
    current_best_fitness = fitness(current_best_solution, K, all_orders, all_riders, dist_mat)

    if current_best_fitness < best_fitness:
        best_solution = current_best_solution
        best_fitness = current_best_fitness
        print(f"Best fitness = {best_fitness}")
        #print(f"Generation {generation}: New best fitness = {best_fitness}")

    # 선택
    selected_population = select_population(population, population_fitness, 19)
    selected_population.append(best_solution)
    selected_population_fitness = [fitness(solution, K, all_orders, all_riders, dist_mat) for solution in selected_population]
    print(f"selection = {selected_population_fitness}")




    return best_solution
