import numpy as np
import random
import time
from itertools import permutations
from util import Bundle, solution_check, select_two_bundles, try_merging_bundles, get_total_distance, get_total_volume, test_route_feasibility, get_cheaper_available_riders, try_bundle_rider_changing
from first_version_simple import algorithm
#from myalgorithm import algorithm

# 1. Initial solution generation(num : 50)
def initialize_population(K, all_orders, all_riders, dist_mat, population_size=50, timelimit=60):
    population = []
    for _ in range(population_size):
        solution = algorithm(K, all_orders, all_riders, dist_mat, timelimit)
        population.append(solution)
    return population

# 2. FItness definition
def fitness(solution, K, all_orders, all_riders, dist_mat):
    checked_solution = solution_check(K, all_orders, all_riders, dist_mat, solution)
    if checked_solution['feasible']:
        return checked_solution['total_cost'] / K  # 목적함수: 총 비용을 주문 수로 나눈 값
    else:
        return float('inf')  # 유효하지 않은 해의 경우 무한대 비용 반환
    
#3. Selection considering fitness
def select_population(population, population_fitness, num_selections):
    #1. 적합도 값이 무한대가 아닌 해 들의 역수의 합을 계산함
    total_fitness = sum(1 / f for f in population_fitness if f != float('inf')) 
    #2. 각 해의 선택 확률을 계산함
    selection_probs = [(1 / f) / total_fitness if f != float('inf') else 0 for f in population_fitness]
    #3. 주어진 확률에 따라 해를 선택함
    selected_population = random.choices(population, weights=selection_probs, k=num_selections)
    return selected_population

#4. CrossOver(we have to check if child is feasible or not after crossover)
def crossover(parent1, parent2, K, all_orders, dist_mat):
    max_attempts = 10  # 최대 시도 횟수 설정
    attempts = 0
    
    while attempts < max_attempts:
        # 교차점 선택
        crossover_point = random.randint(1, len(parent1) - 1)
        
        # 부모 해로부터 자식 해 생성
        child1 = parent1[:crossover_point] + parent2[crossover_point:]
        child2 = parent2[:crossover_point] + parent1[crossover_point:]
        
        # 자식 해가 유효한지 확인
        if is_feasible(child1, K, all_orders, dist_mat) and is_feasible(child2, K, all_orders, dist_mat):
            return child1, child2
        
        attempts += 1
    
    # 최대 시도 횟수를 초과한 경우 부모 해를 반환
    return parent1, parent2


def is_feasible(solution, K, all_orders, dist_mat):
    for bundle_info in solution:
        rider = bundle_info[0]
        shop_seq = bundle_info[1]
        dlv_seq = bundle_info[2]

        # 경로 유효성 테스트
        if test_route_feasibility(all_orders, rider, shop_seq, dlv_seq) != 0:
            return False
    return True

#5. Mutation
def mutate(solution, K, all_orders, all_riders, dist_mat):
    max_attempts = 10  # 최대 시도 횟수 설정
    attempts = 0

    while attempts < max_attempts:
        mutated_solution = solution[:]
        
        # 돌연변이 연산 예시: 랜덤하게 하나의 묶음을 선택하여 순서를 변경
        bundle_index = random.randint(0, len(mutated_solution) - 1)
        bundle_info = mutated_solution[bundle_index]
        
        # 픽업 순서와 배달 순서를 무작위로 섞기
        random.shuffle(bundle_info[1])
        random.shuffle(bundle_info[2])
        
        # 새로운 해가 유효한지 확인
        if is_feasible(mutated_solution, K, all_orders, all_riders, dist_mat):
            return mutated_solution
        
        attempts += 1

    # 최대 시도 횟수를 초과한 경우 원래 해를 반환
    return solution

#6. Replacement(Generation change, Keeping the best solution using elitism)
def replacement(population, new_population, K, all_orders, all_riders, dist_mat, elite_size=2):
    # 기존 세대와 새로운 세대를 결합
    combined_population = population + new_population

    # 적합도 순으로 정렬 (적합도 함수가 낮을수록 좋은 해)
    combined_population.sort(key=lambda sol: fitness(sol, K, all_orders, all_riders, dist_mat))

    # 엘리트 해 유지
    next_generation = combined_population[:elite_size]

    # 나머지 새로운 해들로 채우기
    next_generation += random.sample(combined_population[elite_size:], len(population) - elite_size)

    return next_generation

#Genetic_Algorithm
def genetic_algorithm(K, all_orders, all_riders, dist_mat, population_size=50, generations=100, crossover_rate=0.8, mutation_rate=0.05, elite_size=2, timelimit=60):
    start_time = time.time()

    # 초기 해 생성
    population = initialize_population(K, all_orders, all_riders, dist_mat, population_size, timelimit)
    
    best_solution = None
    best_fitness = float('inf')

    for generation in range(generations):
        if time.time() - start_time > timelimit:
            print("Time limit reached.")
            break

        # 적합도 계산
        population_fitness = [fitness(solution, K, all_orders, all_riders, dist_mat) for solution in population]

        # 현재 세대에서 최적 해 찾기
        current_best_solution = min(population, key=lambda sol: fitness(sol, K, all_orders, all_riders, dist_mat))
        current_best_fitness = fitness(current_best_solution, K, all_orders, all_riders, dist_mat)

        if current_best_fitness < best_fitness:
            best_solution = current_best_solution
            best_fitness = current_best_fitness
            print(f"Generation {generation}: New best fitness = {best_fitness}")

        # 선택
        selected_population = select_population(population, population_fitness, population_size)

        # 교차
        new_population = []
        for i in range(0, len(selected_population), 2):
            parent1 = selected_population[i]
            parent2 = selected_population[i + 1] if i + 1 < len(selected_population) else selected_population[0]
            if random.random() < crossover_rate:
                child1, child2 = crossover(parent1, parent2, K, all_orders, dist_mat)
                new_population.extend([child1, child2])
            else:
                new_population.extend([parent1, parent2])

        # 돌연변이
        for i in range(len(new_population)):
            if random.random() < mutation_rate:
                mutated_solution = mutate(new_population[i], K, all_orders, all_riders, dist_mat)
                if is_feasible(mutated_solution, K, all_orders, all_riders, dist_mat):
                    new_population[i] = mutated_solution

        # 대체
        population = replacement(population, new_population, K, all_orders, all_riders, dist_mat, elite_size)

    # 최적 해 반환
    return best_solution
