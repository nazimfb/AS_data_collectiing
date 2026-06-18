#In case you use an HTTP Authorization header
# Authorization: Basic U0tXR1lRQkE1TElOWUk2VEVQSTNGUU9BOnQ2SjJIVkIzYmJyN3Zrc0UxNzJZOVhqNA==
# login: SKWGYQBA5LINYI6TEPI3FQOA
# pass: t6J2HVB3bbr7vksE172Y9Xj4
# https://rest.db.ripe.net/{source}/{objecttype}/{key}
# https://rest-test.db.ripe.net/{source}/{objecttype}/{key}
# source -> ripe or test
# objectType -> person
# key -> PP1-RIPE
# key -> TP1-RIPE
# key -> AA1-TEST

import requests
url = "https://rest-test.db.ripe.net/ripe/ris-asns/data.json"
custom_headers = {
    "Content-Type": "application/json",
    "Authorization": "Basic U0tXR1lRQkE1TElOWUk2VEVQSTNGUU9BOnQ2SjJIVkIzYmJyN3Zrc0UxNzJZOVhqNA=="
}
response = requests.get(url,headers=custom_headers)
print(response)

try:
    # Send the GET request
    response = requests.get(url,headers=custom_headers)
    
    # Check if the request was successful (Status code 200-299)
    if response.status_code == 200:
        # Parse the JSON response into a Python dictionary
        data = response.json()
        print("Success!")
        print(data)
    else:
        print(f"Server returned status code: {response.status_code}")
        
except requests.exceptions.RequestException as e:
    # Handle connection errors, timeouts, etc.
    print(f"An error occurred: {e}")
