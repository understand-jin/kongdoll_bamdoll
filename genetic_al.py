import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, Rider, Order, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm
from Assistance import initialize_population, fitness


#Genetic_Algorithm
def genetic_algorithm(K, all_orders, all_riders, dist_mat, population_size, generations, crossover_rate=0.8, mutation_rate=0.05, elite_size=2, timelimit=60):
    start_time = time.time()

    # 초기 해 생성
    population = initialize_population(K, all_orders, all_riders, dist_mat, population_size, timelimit)
    
    best_solution = None
    best_fitness = float('inf')
    print(f"bestbest : {best_fitness}")

    for generation in range(generations):
        if time.time() - start_time > timelimit:
            print("Time limit reached.")
            break

        # 적합도 계산
        population_fitness = [fitness(solution, K, all_orders, all_riders, dist_mat) for solution in population]
        print(population_fitness)

        # 현재 세대에서 최적 해 찾기
        # current_best_solution = min(population, key=lambda sol: fitness(sol, K, all_orders, all_riders, dist_mat))
        # current_best_fitness = fitness(current_best_solution, K, all_orders, all_riders, dist_mat)

        # if current_best_fitness < best_fitness:
        #     best_solution = current_best_solution
        #     best_fitness = current_best_fitness
        #     print(f"Generation {generation}: New best fitness = {best_fitness}")

        # 선택
        # selected_population = select_population(population, population_fitness, population_size)
        # print(f"selected_value : {selected_population}")

        # 교차
        # new_population = []
        # for i in range(0, len(selected_population), 2):
        #     parent1 = selected_population[i]
        #     parent2 = selected_population[i + 1] if i + 1 < len(selected_population) else selected_population[0]
        #     if random.random() < crossover_rate:
        #         child1, child2 = crossover(parent1, parent2, K, all_orders, dist_mat)
        #         new_population.extend([child1, child2])
        #     else:
        #         new_population.extend([parent1, parent2])

        # 돌연변이
        # for i in range(len(new_population)):
        #     if random.random() < mutation_rate:
        #         mutated_solution = mutate(new_population[i], K, all_orders, all_riders, dist_mat)
        #         if is_feasible(mutated_solution, K, all_orders, all_riders, dist_mat):
        #             new_population[i] = mutated_solution

        # 대체
        # population = replacement(population, new_population, K, all_orders, all_riders, dist_mat, elite_size)

    # 최적 해 반환
    return best_solution
