import json
import numpy as np

def calculate_efficiencies(file_path):
    # JSON 파일 읽기
    with open('C:\LG Algorithm\stage1_problems\STAGE1_3.json', 'r') as file:
        data = json.load(file)

    # 데이터 변수 설정
    K = data['K']
    riders = data['RIDERS']
    orders = data['ORDERS']
    dist_matrix = np.array(data['DIST'])

    # 모든 주문의 부피 평균 계산
    order_volumes = [order[7] for order in orders]
    avg_volume = np.mean(order_volumes)

    # d1, d2, d3 계산
    d1 = np.sum(dist_matrix[:K, :K]) / 2500
    d2 = np.sum(dist_matrix[:K, K:2*K]) / 2500
    d3 = np.sum(dist_matrix[K:2*K, K:2*K]) / 2500

    # 각 배달원의 효율성 지표 계산 함수
    def calculate_efficiency(rider, avg_volume, d1, d2, d3):
        capacity = rider[2]
        variable_cost = rider[3]
        fixed_cost = rider[4]
        
        Ri = (0.8 * capacity) / avg_volume
        Xi = (Ri - 1) * d1 + (Ri - 1) * d3 + d2
        efficiency = fixed_cost + (Xi / 100) * variable_cost
        
        return efficiency

    # 각 배달원의 효율성 지표 계산
    efficiencies = []
    for rider in riders:
        rider_type = rider[0]
        efficiency = calculate_efficiency(rider, avg_volume, d1, d2, d3)
        efficiencies.append([rider_type, efficiency])

    # 효율성 지표 반환
    return efficiencies
