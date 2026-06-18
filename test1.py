import csv
import requests

# RIPEstat endpoint for all active global ASNs
url = "https://stat.ripe.net/data/ris-asns/data.json"
params = {"list_asns": "true"}
csv_filename = "global_asns.csv"

try:
    print("Fetching data from RIPE API (this may take a few seconds)...")
    response = requests.get(url, params=params, timeout=20)
    
    if response.status_code == 200:
        data = response.json()
        asn_list = data["data"]["asns"]
        
        # Open a new CSV file to write the data
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            
            # Write the header row
            writer.writerow(["ASN"])
            
            # Write each ASN as a new row
            for asn in asn_list:
                writer.writerow([asn])
                
        print(f"Success! Saved {len(asn_list)} ASNs to '{csv_filename}'.")
    else:
        print(f"Failed to fetch data. Server status code: {response.status_code}")
        
except requests.exceptions.RequestException as e:
    print(f"Network error occurred: {e}")
