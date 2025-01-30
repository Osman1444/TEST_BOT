import random
import time

# List to store used APIs
used_apis = []

with open('GeminiAPI.txt', 'r') as f:
    all_apis = [api.strip() for api in f.readlines()]

def get_random_api():
    global used_apis
    # Get available APIs (ones that haven't been used)
    available_apis = [api for api in all_apis if api not in used_apis]
    
    # If all APIs have been used, reset the used_apis list
    if not available_apis:
        used_apis.clear()
        available_apis = all_apis
    
    # Select a random API from available ones
    selected_api = random.choice(available_apis)
    used_apis.append(selected_api)
    return selected_api


while True:
    GeminiAPI = get_random_api()
    print(GeminiAPI)
    print(used_apis)