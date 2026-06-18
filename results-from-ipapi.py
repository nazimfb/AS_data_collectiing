import csv
import os
import time
import requests

ASN_TXT_URL = "https://ripe.net"
DATA_CSV = "ripe_asn_data.csv"

# Free tier limit configuration (Adjust if you have a paid plan key)
API_LIMIT = 1000  
HEADERS = {
    "User-Agent": "ASNMissingRecovery/1.0 (Contact: your_email@example.com)"
}

def get_all_global_asns():
    """Downloads the master global text list from RIPE."""
    print(f"Downloading master global ASN list from {ASN_TXT_URL}...")
    response = requests.get(ASN_TXT_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()

    global_set = set()
    for line in response.text.splitlines():
        if line.strip():
            parts = line.split()
            if parts:
                global_set.add(f"AS{parts[0]}")
    return global_set

def get_already_saved_asns():
    """Reads your existing data CSV to see what you have already successfully stored."""
    if not os.path.exists(DATA_CSV):
        print(f"Error: Target file '{DATA_CSV}' does not exist yet.")
        return set()
        
    saved_set = set()
    with open(DATA_CSV, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Asn"):
                saved_set.add(row["Asn"].strip())
    return saved_set

def fetch_missing_asn_details(formatted_asn):
    """Queries ipapi.is and maps all deep metadata fields to your schema."""
    # endpoint takes queries in lowercase format (e.g., as1)
    url = f"https://ipapi.is{formatted_asn.lower()}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            data = res.json()
            asn_data = data.get("asn", {})
            
            # Combine IPv4 and IPv6 arrays safely into a single string
            ipv4_prefixes = asn_data.get("prefixes", [])
            ipv6_prefixes = asn_data.get("prefixesIPv6", [])
            all_cidrs = ipv4_prefixes + ipv6_prefixes
            cidr_string = ", ".join(all_cidrs) if all_cidrs else ""
            
            # Map parameters perfectly to your specific column naming conventions
            return {
                "Asn": formatted_asn,
                "country_code": asn_data.get("country", ""),
                "isp_name": asn_data.get("org", "Unknown Global Holder"),
                "start_date": asn_data.get("created", ""),      # <-- Captured from sample
                "end_date": "",
                "db_insert_date": asn_data.get("created", ""),  # <-- Captured from sample
                "modified_date": asn_data.get("updated", ""),   # <-- Captured from sample
                "cidr": cidr_string,                            # <-- Combined IPv4 + IPv6
                "fk_asn": ""
            }
        elif res.status_code == 429:
            print("\n[!] Warning: Hit ipapi.is rate limit quota limits.")
            return "RATE_LIMIT"
    except Exception as e:
        print(f"Connection glitch fetching {formatted_asn}: {e}")
    return None

def main():
    try:
        global_asns = get_all_global_asns()
    except Exception as e:
        print(f"Failed to fetch global inventory master dump: {e}")
        return

    saved_asns = get_already_saved_asns()
    missing_asns = sorted(list(global_asns - saved_asns), key=lambda x: int(x[2:]))

    print(f"\n--- Analysis Results ---")
    print(f"Total global ASNs available: {len(global_asns)}")
    print(f"Currently in your CSV file: {len(saved_asns)}")
    print(f"Missing ASNs detected:       {len(missing_asns)}")
    print(f"------------------------\n")

    if not missing_asns:
        print("Everything matches! Your CSV file is already perfectly complete.")
        return

    run_limit = min(len(missing_asns), API_LIMIT)
    print(f"Starting processing batch recovery for the first {run_limit} missing records...")

    csv_headers = ["Asn", "country_code", "isp_name", "start_date", "end_date", "db_insert_date", "modified_date", "cidr", "fk_asn"]

    with open(DATA_CSV, mode="a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
        
        success_count = 0
        for count, target_asn in enumerate(missing_asns[:run_limit], 1):
            print(f"[{count}/{run_limit}] Recovering {target_asn}...", end="\r")
            
            row_data = fetch_missing_asn_details(target_asn)
            
            if row_data == "RATE_LIMIT":
                break
                
            if row_data:
                writer.writerow(row_data)
                success_count += 1
                
            time.sleep(0.5)

    print(f"\nCompleted run! Successfully recovered and added {success_count} missing ASNs with complete metadata to '{DATA_CSV}'.")

if __name__ == "__main__":
    main()
