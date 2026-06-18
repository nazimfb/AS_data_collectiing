import csv
import requests

# Files
input_csv = "global_asns.csv"
output_csv = "global_asns_detailed.csv"

# Step 1: Download RIPE's master list of ASN names
print("Downloading the global ASN name mapping database from RIPE...")
ripe_text_url = "https://ftp.ripe.net/ripe/asnames/asn.txt"

# CRITICAL: This User-Agent stops the server from returning HTML redirect pages
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(ripe_text_url, headers=headers, timeout=30)
    response.raise_for_status()
    raw_lines = response.text.splitlines()
    print(f"Download complete! Found {len(raw_lines)} master records.")
except Exception as e:
    print(f"Failed to download the RIPE master mapping file: {e}")
    exit()

# Step 2: Parse the master file into a fast-lookup dictionary
print("Processing master records...")
asn_map = {}
for line in raw_lines:
    line_clean = line.strip()
    if not line_clean or line_clean.startswith("<!DOCTYPE"):
        continue  # Safeguard against accidental HTML leaking through
        
    # The file layout looks like: "3333 RIPE-NCC-AS RIPE Network Coordination Centre, NL"
    parts = line_clean.split(" ", 1)
    if len(parts) == 2:
        asn_num = parts[0].strip()  # e.g., "3333"
        details = parts[1].strip()  # e.g., "RIPE-NCC-AS RIPE Network Coordination Centre, NL"
        
        # Safely extract the 2-letter country code if it sits past a comma at the end
        country = "N/A"
        if "," in details:
            possible_country = details.split(",")[-1].strip()
            if len(possible_country) == 2 and possible_country.isupper():
                country = possible_country
        
        asn_map[asn_num] = {
            "details": details,
            "country": country
        }

# Step 3: Read your file and cross-reference everything instantly
print(f"Reading '{input_csv}' to match data...")
detailed_rows = []

try:
    with open(input_csv, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        header = next(reader)  # Skip "ASN" header row
        
        for row in reader:
            if not row:
                continue
            
            # Extract the raw ASN string from the list structure
            clean_asn = row[0].strip()
            
            # Match against our dictionary keys
            if clean_asn in asn_map:
                holder_info = asn_map[clean_asn]["details"]
                country_info = asn_map[clean_asn]["country"]
            else:
                holder_info = "Unknown / Unregistered Holder"
                country_info = "N/A"
                
            detailed_rows.append([clean_asn, holder_info, country_info])
            
except FileNotFoundError:
    print(f"Error: Could not find '{input_csv}'.")
    exit()

# Step 4: Save the final dataset
print(f"Saving all {len(detailed_rows)} detailed records to '{output_csv}'...")
with open(output_csv, mode="w", newline="", encoding="utf-8") as outfile:
    writer = csv.writer(outfile)
    writer.writerow(["ASN", "Holder_and_Description", "Country"])
    writer.writerows(detailed_rows)

print("Process completely finished! Open 'global_asns_detailed.csv' to view your results.")
