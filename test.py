# mock_robot.py
import time
import json

# Sample data that mimics robot output
test_sequence = [
    {"node_id": "Rt_", "distance": 0, "possible_ways": {"F": True}},
    {"node_id": "Rt_F", "distance": 10, "possible_ways": {"L": True, "R": True}},
    {"node_id": "Rt_FL", "distance": 20, "possible_ways": {"F": True}},
    {"node_id": "Rt_FLF", "distance": 30, "possible_ways": {"L": True, "R": True}},
    {"node_id": "Rt_FLFR", "distance": 40, "possible_ways": {}},
]

if __name__ == "__main__":
    for data in test_sequence:
        print(json.dumps(data))  # Prints JSON to stdout
        time.sleep(1)  # Simulate delay between commands
