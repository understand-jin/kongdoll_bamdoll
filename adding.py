import random
from util import *

problem_file = 'STAGE1_1.json'
# problem_file = "TEST_K50_1.json"
timelimit = 30

# np.random.seed(1)

with open(problem_file, 'r') as f:
    prob = json.load(f)

K = prob['K']

ALL_ORDERS = [Order(order_info) for order_info in prob['ORDERS']]
ALL_RIDERS = [Rider(rider_info) for rider_info in prob['RIDERS']]

DIST = np.array(prob['DIST'])
for r in ALL_RIDERS:
    r.T = np.round(DIST/r.speed + r.service_time)

def crossover(parent1, parent2, K, all_orders, dist_mat):
    max_attempts = 100  # 최대 시도 횟수 설정
    attempts = 0
    
    while attempts < max_attempts:
        size = len(parent1)
        child1, child2 = [None] * size, [None] * size

        # 두 교차점 무작위 선택
        cxpoint1, cxpoint2 = sorted(random.sample(range(size), 2))

        # 부모의 일부 구간을 자식에게 복사
        child1[cxpoint1:cxpoint2] = parent1[cxpoint1:cxpoint2]
        child2[cxpoint1:cxpoint2] = parent2[cxpoint1:cxpoint2]

        def fill_child(child, parent):
            for i in range(len(parent)):
                if i >= cxpoint1 and i < cxpoint2:
                    continue
                if parent[i] not in child:
                    child[i] = parent[i]
                else:
                    # 매핑 관계를 따라 요소를 조정
                    swap_val = parent[i]
                    while swap_val in child:
                        swap_val = parent[parent.index(swap_val)]
                    child[i] = swap_val

        fill_child(child1, parent2)
        fill_child(child2, parent1)

        if is_feasible(child1, K, all_orders, dist_mat):
            return child1, child2

        if is_feasible(child2, K, all_orders, dist_mat):
            return child1, child2
        
        attempts += 1
        print("not feasible")
    
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

# 예제 부모 솔루션

parent1 = [['BIKE', [8, 18], [8, 18]], ['BIKE', [6, 20], [6, 20]], ['BIKE', [70, 56], [56, 70]], ['BIKE', [22, 33], [22, 33]], ['BIKE', [55, 39], [39, 55]], ['BIKE', [93, 86], [86, 93]], ['BIKE', [42, 53], [42, 53]], ['BIKE', [99, 96], [96, 99]], ['BIKE', [28, 35], [28, 35]], ['BIKE', [19, 27], [19, 27]], ['BIKE', [51, 44], [51, 44]], ['BIKE', [12, 0], [0, 12]], ['BIKE', [13, 9], [13, 9]], ['BIKE', [2, 17], [2, 17]], ['BIKE', [32, 11], [11, 32]], ['BIKE', [34, 15], [15, 34]], ['BIKE', [29, 54], [29, 54]], ['BIKE', [26, 62], [26, 62]], ['BIKE', [41, 1], [1, 41]], ['BIKE', [5, 4], [4, 5]], ['WALK', [82], [82]], ['WALK', [72], [72]], ['CAR', [24, 30], [30, 24]], ['CAR', [78, 90], [90, 78]], ['CAR', [77, 80], [77, 80]], ['CAR', [59, 89], [59, 89]], ['CAR', [91, 84], [91, 84]], ['CAR', [49, 47], [47, 49]], ['CAR', [23, 58], [23, 58]], ['CAR', [43, 48], [43, 48]], ['CAR', [66, 52], [52, 66]], ['CAR', [38, 21], [21, 38]], ['CAR', [95, 94], [95, 94]], ['CAR', [14, 46], [14, 46]], ['CAR', [37, 63], [37, 63]], ['CAR', [61, 68], [61, 68]], ['CAR', [57, 67], [67, 57]], ['CAR', [16, 10], [10, 16]], ['CAR', [31, 64], [31, 64]], ['CAR', [3], [3]], ['CAR', [45, 40], [45, 40]], ['CAR', [99], [99]], ['CAR', [55], [55]], ['CAR', [31, 64], [31, 64]], ['CAR', [49, 59], [49, 59]], ['CAR', [89, 76], [76, 89]], ['CAR', [78], [78]], ['CAR', [36, 65], [36, 65]], ['CAR', [91], [91]], ['CAR', [86, 93], [86, 93]], ['CAR', [80], [80]], ['CAR', [85, 79], [79, 85]], ['CAR', [73, 83], [73, 83]], ['CAR', [69], [69]], ['CAR', [71], [71]]]
parent2 = [['BIKE', [5, 4], [4, 5]], ['BIKE', [0, 11], [0, 11]], ['BIKE', [12, 38], [12, 38]], ['BIKE', [15, 23], [15, 23]], ['BIKE', [9, 13], [13, 9]], ['BIKE', [29, 54], [29, 54]], ['BIKE', [96, 68], [68, 96]], ['BIKE', [30, 24], [30, 24]], ['BIKE', [82, 61], [61, 82]], ['BIKE', [51, 44], [51, 44]], ['BIKE', [37, 33], [33, 37]], ['BIKE', [26, 62], [26, 62]], ['BIKE', [14, 46], [14, 46]], ['BIKE', [19, 27], [19, 27]], ['BIKE', [42, 53], [42, 53]], ['BIKE', [10, 32], [10, 32]], ['BIKE', [20, 34], [20, 34]], ['BIKE', [52, 66], [52, 66]], ['BIKE', [3, 1], [3, 1]], ['BIKE', [22, 58], [22, 58]], ['CAR', [28, 35], [28, 35]], ['CAR', [25, 50], [25, 50]], ['CAR', [16, 21], [21, 16]], ['CAR', [57, 67], [67, 57]], ['CAR', [97], [97]], ['CAR', [81, 92], [81, 92]], ['CAR', [6, 47], [6, 47]], ['CAR', [18, 7], [7, 18]], ['CAR', [8], [8]], ['CAR', [48, 77], [48, 77]], ['CAR', [84, 90], [90, 84]], ['CAR', [41, 56], [41, 56]], ['CAR', [2, 39], [2, 39]], ['CAR', [88, 87], [88, 87]], ['CAR', [94, 95], [95, 94]], ['CAR', [70, 60], [60, 70]], ['CAR', [63], [63]], ['CAR', [75, 72], [72, 75]], ['CAR', [45, 40], [45, 40]], ['CAR', [74, 98], [74, 98]], ['CAR', [17, 43], [17, 43]], ['CAR', [7], [7]], ['CAR', [25, 50], [25, 50]], ['CAR', [60, 65], [60, 65]], ['CAR', [71, 97], [71, 97]], ['CAR', [88, 87], [88, 87]], ['CAR', [83, 69], [69, 83]], ['CAR', [81, 92], [81, 92]], ['CAR', [98, 85], [85, 98]], ['CAR', [75, 79], [75, 79]], ['CAR', [76, 74], [76, 74]], ['CAR', [36], [36]], ['CAR', [73], [73]]]

# 교차 수행
child1, child2 = crossover(parent1, parent2, K, ALL_ORDERS, DIST)
print(f"Child1: {child1}")
print(f"Child2: {child2}")
