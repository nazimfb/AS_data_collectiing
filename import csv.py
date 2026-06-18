import concurrent.futures
import csv
import os
import threading
import time
import requests

ASN_TXT_URL = "https://ftp.ripe.net/ripe/asnames/asn.txt"
# FIX 1: Keep the database tier pathway lower-case to stop gateway routing rejections
AUT_NUM_RIPE_URL = "https://rest.db.ripe.net/ripe/aut-num/"
SEARCH_URL = "https://rest.db.ripe.net/search.json"
OUTPUT_CSV = "ripe_asn_data.csv"
PROGRESS_FILE = "processed_asns.txt"

MAX_THREADS = 10  
HEADERS = {
    "User-Agent": "ASNDataFetcherResumable/1.0 (Contact: your_email@example.com)"
}
file_lock = threading.Lock()


def get_all_asns():
    print(f"Downloading ASN list from {ASN_TXT_URL}...")
    response = requests.get(ASN_TXT_URL, headers=HEADERS) # Added headers here too for consistency
    response.raise_for_status()

    asn_list = []
    for line in response.text.splitlines():
        if line.strip():
            parts = line.split()
            if parts:
                asn_list.append(parts[0])
    return asn_list


def load_processed_asns():
    if not os.path.exists(PROGRESS_FILE):
        return set()
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def extract_attribute_value(attributes_list, name_to_find):
    for attr in attributes_list:
        if attr.get("name") == name_to_find:
            return attr.get("value")
    return None


def fetch_cidrs_for_asn(formatted_asn):
    """Queries RIPE for route/route6 objects originating from this ASN to extract CIDRs."""
    params = {
        "query-string": formatted_asn,
        "inverse-attribute": "origin",
        "type-filter": ["route", "route6"]
    }
    try:
        res = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=10)
        if res.status_code != 200:
            return ""
        
        data = res.json()
        objects = data.get("objects", {}).get("object", [])
        
        cidrs = []
        for obj in objects:
            attrs = obj.get("attributes", {}).get("attribute", [])
            cidr_val = extract_attribute_value(attrs, "route") or extract_attribute_value(attrs, "route6")
            if cidr_val:
                cidrs.append(cidr_val)
                
        return ", ".join(cidrs)
    except Exception:
        return ""


def fetch_single_asn(asn):
    formatted_asn = f"AS{asn}"
    
    row_data = {
        "Asn": formatted_asn,
        "country_code": "",
        "isp_name": "",
        "start_date": "",
        "end_date": "",
        "db_insert_date": "",
        "modified_date": "",  
        "cidr": "",
        "fk_asn": "",
    }

    try:
        # 1. Fetch aut-num object
        aut_num_url = f"{AUT_NUM_RIPE_URL}{formatted_asn}.json"
        aut_num_res = requests.get(aut_num_url, headers=HEADERS, timeout=10)

        if aut_num_res.status_code == 404:
            return "skipped_404", row_data

        aut_num_res.raise_for_status()
        aut_num_data = aut_num_res.json()

        objects = aut_num_data.get("objects", {}).get("object", [])
        if not objects:
            return "no_data", row_data

        aut_num_attrs = objects[0].get("attributes", {}).get("attribute", [])
        
        # Populate dates from aut-num metadata
        row_data["db_insert_date"] = extract_attribute_value(aut_num_attrs, "created")
        row_data["modified_date"] = extract_attribute_value(aut_num_attrs, "last-modified")  

        # FIX 2: Capture the actual downstream sub-entity or campus name from the description field
        sub_entity_name = extract_attribute_value(aut_num_attrs, "descr")

        # 2. Fetch CIDR Blocks mapping to this ASN
        row_data["cidr"] = fetch_cidrs_for_asn(formatted_asn)

        # 3. Look for organization link
        org_id = None
        for attr in aut_num_attrs:
            if attr.get("name") == "org":
                org_id = attr.get("value")
                break

        # Fetch organisation object details if it exists
        if org_id:
            org_url = f"https://rest.db.ripe.net/ripe/organisation/{org_id}.json"
            org_res = requests.get(org_url, headers=HEADERS, timeout=10)

            if org_res.status_code == 200:
                org_data = org_res.json()
                org_objects = org_data.get("objects", {}).get("object", [])

                if org_objects:
                    org_attrs = org_objects[0].get("attributes", {}).get("attribute", [])
                    row_data["country_code"] = extract_attribute_code = extract_attribute_value(org_attrs, "country")
                    parent_org_name = extract_attribute_value(org_attrs, "org-name") or ""
                    
                    # Merge Parent name and Sub-entity/campus name cleanly if they are distinct
                    if sub_entity_name and sub_entity_name.lower() not in parent_org_name.lower():
                        row_data["isp_name"] = f"{parent_org_name} ({sub_entity_name})"
                    else:
                        row_data["isp_name"] = parent_org_name
        
        # Fallback if no org link object exists but a description field is present
        if not row_data["isp_name"] and sub_entity_name:
            row_data["isp_name"] = sub_entity_name

        return "success", row_data

    except Exception as e:
        return f"error: {str(e)}", row_data


def save_progress(asn, status, row_data, csv_headers):
    with file_lock:
        if status == "success":
            file_exists = os.path.exists(OUTPUT_CSV)
            with open(OUTPUT_CSV, mode="a", newline="", encoding="utf-8") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row_data)

        with open(PROGRESS_FILE, "a", encoding="utf-8") as prog_file:
            prog_file.write(f"{asn}\n")


def main():
    csv_headers = [
        "Asn",
        "country_code",
        "isp_name",
        "start_date",
        "end_date",
        "db_insert_date",
        "modified_date",
        "cidr",
        "fk_asn",
    ]

    try:
        all_asns = get_all_asns()
    except Exception as e:
        print(f"Failed to fetch the master ASN list: {e}")
        return

    processed_asns = load_processed_asns()
    asns_to_process = [asn for asn in all_asns if asn not in processed_asns]

    print(f"Total ASNs in master list: {len(all_asns)}")
    print(f"Already processed: {len(processed_asns)}")
    print(f"Remaining ASNs to process: {len(asns_to_process)}")

    if not asns_to_process:
        print("All ASNs have already been processed successfully!")
        return

    print(f"Starting multithreaded processing with {MAX_THREADS} threads...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_asn = {
            executor.submit(fetch_single_asn, asn): asn
            for asn in asns_to_process
        }

        count = 0
        for future in concurrent.futures.as_completed(future_to_asn):
            asn = future_to_asn[future]
            try:
                status, row_data = future.result()
                save_progress(asn, status, row_data, csv_headers)

                count += 1
                if count % 10 == 0:
                    print(f"Progress updated: Processed {count} additional ASNs.")

                # Small throttle gap so thread workers share socket pool space gently
                time.sleep(0.05)

            except Exception as exc:
                print(f"ASN {asn} generated an unhandled exception: {exc}")


if __name__ == "__main__":
    main()
