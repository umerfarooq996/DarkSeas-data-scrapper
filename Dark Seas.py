import os
import re
import json
import time
import random
import openpyxl
import traceback
import pandas as pd

import requests
from selenium import webdriver
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC

from config import email, password

from script import (
    get_walmart_product_data,
    get_shopify_product_data,
    get_ebay_product_data,
    get_amazon_product_data,
)


CHROME_DIRECTORY = os.path.abspath("../ChromeUserDirectory")

male_gender = {"gender": "Male", "age_group": "adult", "title_gender": "Men's"}

dark_seas_mens_dict = {
    # "All Mens": {
    #     "id": "2136",
    #     "gender": male_gender,
    # },
    # #-----------------------Top/Knits---------------------
    # "Knits": {
    #     "id": "1490",
    #     "lookup":"Shirt"
    # },
    # #-----------------------Top/Woven---------------------
    # "Woven": {
    #     "id": "1491",
    #     "lookup":"Shirt"
    # },
    "Jackets": {"id": "1455", "lookup": "Jacket"},
    # #-----------------------Bottoms/Bottoms/---------------------
    # "Bottoms": {
    #     "id": "1977",
    #     "lookup":"Pants"
    # },
    "Sweater": {"id": "2590", "lookup": "Sweater"},
    "Tees": {"id": "2587", "lookup": "Tee"},
    # "Fleece": {
    #     "id": "2588",
    #     "lookup":""
    # },
    "Headwear": {"id": "1454", "lookup": "Hat"},
    # "Accessories": {
    #     "id": "1450",
    #     "lookup":"Accessories"
    # },
}

loser_machine_dict = {
    #     "All Mens": {
    #         "id": "2027",
    #         "gender": male_gender,
    #     },
    "Jackets": {"id": "1445", "lookup": "Jacket"},
    #     "Vests": {
    #         "id": "1448",
    #         "gender": male_gender,
    #     },
    #     # -----------------------Top/Knits---------------------
    #     "Knits": {
    #         "id": "1469",
    #         "gender": male_gender,
    #     },
    #     # -----------------------Top/Woven---------------------
    #     "Woven": {
    #         "id": "1470",
    #         "gender": male_gender,
    #     },
    #     "Fleece": {
    #         "id": "4788",
    #         "gender": male_gender,
    #     },
    "Tees": {"id": "2579", "lookup": "Tee"},
    #     "Bottoms": {
    #         "id": "2591",
    #         "gender": male_gender,
    #     },
    "Headwear": {"id": "1443", "lookup": "Hat"},
    #     # -----------------------Accessories/Gloves---------------------
    #     "Gloves": {
    #         "id": "1449",
    #         "gender": male_gender,
    #     },
    #     # -----------------------Accessories/Misc---------------------
    #     "Misc": {
    #         "id": "1480",
    #         "gender": male_gender,
    #     },
}


loopkup_df = pd.read_excel("Lookup_Table.xlsx")


def get_product_type(key):
    for row in loopkup_df.values.tolist():
        if key in row[0]:
            return {
                "category": row[1],
                "type": row[2],
                "weight": row[3],
            }


def add_item_data(dic, gen):
    for key in dic.keys():
        dic[key]["gender"] = gen
        cat = get_product_type(dic[key]["lookup"])
        if cat:
            dic[key].update(cat)
        else:
            print("Not found lookup  -> ", dic[key]["lookup"])


add_item_data(dark_seas_mens_dict, male_gender)
add_item_data(loser_machine_dict, male_gender)
# print(dark_seas_mens_dict)


products_data = []
export_switch = True

VENDOR = "Dark Seas"

quantity = []
debug_quantity = []
pro_details = []


def get_details(var):
    quantity = []
    debug_quantity = []
    all_product_details = []
    available = True
    try:
        # FIXME no description and bulletpoints
        description = ""
        bullet_points = []
        details_dict = {
            "cost": None,
            "price": None,
            # Store the style_code for the current product
            "style_code": var["productNumber"],
            "title": var["productName"],
            "color": var["colorName"],
            "description": description,
            "features": [],
            "images": [],
            "sizes": [],
            "bullet_points": bullet_points,
            "stock": [],
        }
        image_keys = [
            "imageUrl",
            "image2Url",
            "image3Url",
            "image4Url",
            "image5Url",
            "image6Url",
        ]
        for img in image_keys:
            if img in var.keys():
                details_dict["images"].append(var[img])
        # if var['productNumber']=="102000074-HCH":
        # 	pass
        for size, val in var["groupSizeList"][0].items():
            idx = 0
            unit_price = val[idx]["unitPrice"]
            unit_price = round(unit_price)
            msrp = round(unit_price * 2)
            if not details_dict["cost"] and not details_dict["price"]:
                details_dict["cost"] = unit_price
                details_dict["price"] = msrp
            available_date = val[idx]["availableDate"]
            if available_date != "AO":
                available = False
            # dt = {"SKU": f'{details_dict["style_code"]}-{size}', 'Upc': val[idx]["upc"],
            # "Quantity": val[idx]["inventory"], "Cost": unit_price, "Price": msrp}
            # print(val)
            upc = ""
            try:
                upc = val[idx]["upc"]
            except:
                print("Upc not found -> ", var["productNumber"], size)
            details_dict["stock"].append(
                {
                    "SKU": f"{details_dict['style_code']}-{size}",
                    "size": size,
                    "Upc": upc,
                    "Quantity": val[idx]["inventory"],
                    "Cost": unit_price,
                    "Price": msrp,
                    "code": details_dict["style_code"],
                }
            )
            if available:
                # quantity.append(dt)
                details_dict["sizes"].append(size)
            else:
                pass
                # dt["Available Date"] = available_date
                # debug_quantity.append(dt)
    except:
        print(var["productNumber"])
        #        with open("temp.json", "w") as file:
        #            json.dump(var, file)
        traceback.print_exc()
    if not available:
        details_dict = None
    return details_dict, quantity, debug_quantity


def getDescription(a1, a2, a3, a4):
    a2 = [f"<li>{x}</li>" for x in a2]
    a2 = "".join(a2)
    a2 = f"<ul>{a2}</ul>".replace("’", "'")
    a4 = [f"<li>{x}</li>" for x in a4]
    a4 = "".join(a4)
    a4 = f"<div><span>Features:</span> <ul>{a4}</ul></div>".replace("’", "'")
    a1 = f"<div>{a1}</div>"
    a3 = f"<div><span>Style #:</span><span>{a3}</span></div>"
    desc = f"{a1}{a2}{a4}{a3}"
    return desc


def getCost(p):
    if p:
        p = p.replace("$", "").strip()
        p = round(float(p))
        p = int(p)
        return p


def try_again(ls, ind):
    try:
        return ls[ind]
    except:
        return None


def remove_double_spaces(text):
    return re.sub(r" +", " ", text)


def scrapper(data, dt):
    for prd in data["detail"]:
        var, qu, d_qu = get_details(prd)
        quantity.extend(qu)
        debug_quantity.extend(d_qu)
        if var:
            var.update(dt)
            try:
                var["url"] = None
                var["widths"] = []
                products_data.append(var)
            except:
                traceback.print_exc()
                input(var)


def scrap(session_token, vendor, dt):
    for key, value in dt.items():
        print(f"Fetching -> {vendor} {key}")
        data = get_json(session_token, value["id"])
        os.makedirs(vendor, exist_ok=True)
        with open(f"{os.path.join(vendor,key)}.json", "w") as file:
            json.dump(data, file)
        # with open(f"{os.path.join(vendor,key)}.json", "r") as file:
        #     data = json.load(file)
        # scrapper(data, value)

    file_path = "Template.xlsx"  # Replace with the path to your existing Excel file
    workbook = openpyxl.load_workbook(file_path)
    get_shopify_product_data(products_data, vendor, workbook)
    get_ebay_product_data(products_data, vendor, workbook)
    get_walmart_product_data(products_data, vendor, workbook)
    get_amazon_product_data(products_data, vendor, workbook)

    current_date = datetime.now().strftime("%Y-%m-%d")
    workbook.save(f"{vendor}_{current_date}.xlsx")
    workbook.close()
    pd.DataFrame(debug_quantity).to_csv(
        f"Debug_{vendor}_{current_date}.xlsx", index=False
    )

    # add_upc_barcode(quantity)
    # pd.DataFrame(quantity).drop_duplicates(subset=['SKU']).to_csv(f"{vendor} Quantity.csv", index=False)
    # pd.DataFrame(debug_quantity).drop_duplicates(subset=['SKU']).to_csv(f"{vendor} Quantity Debug.csv", index=False)


def main():
    session_token = get_browser_session_token()
    print("*" * 50, "Dark Seas", "*" * 50)
    scrap(session_token, "Dark Seas", dark_seas_mens_dict)
    products_data.clear()
    print("*" * 50, "Loser Machine", "*" * 50)
    scrap(session_token, "Loser Machine", loser_machine_dict)


def add_upc_barcode(quantity):
    for d_r, q_r in zip(products_data, quantity):
        if d_r["Variant SKU"] != q_r["SKU"]:
            print("Not found in upc barcode -> ", d_r["Variant SKU"])
        else:
            d_r["Variant Barcode"] = q_r["Upc"]
            d_r["Google Shopping / MPN"] = q_r["Upc"]


def get_size(size):
    try:
        size = int(size)
        if (
            len(str(size)) > 1
            and size != 10
            and size != 11
            and size != 12
            and size != 13
            and size != 14
            and size != 15
            and size != 16
        ):
            size = int(size) / 10
        return size
    except (ValueError, TypeError):
        raise ValueError(f"Invalid size: {size}")


def get_json(session_token, id):
    headers = {
        "sec-ch-ua": '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://darkseas.hubsoft.com/availability/menus/2136/gallery?from=0&to=4",
        "sec-ch-ua-mobile": "?1",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.36",
        "sec-ch-ua-platform": '"Android"',
    }

    params = {
        "viewType": "L",
        "preSeason": "0",
        "pageSize": "1000",
        "startIndex": "0",
        "markFavorites": "1",
        "includeAllSeason": "1",
        "showOnlyImmedAvail": "0",
        "showOnlyAvail": "0",
        "showIfAvailAllSize": "0",
        "sortProdBy": "seasonOrder",
        "subMenuId": id,
        "warehouseId": "449",
        "sessionToken": session_token,
    }

    response = requests.get(
        "https://darkseas.hubsoft.com/cxf/order2/getDraftOrderItems",
        params=params,
        headers=headers,
    )
    return response.json()


def get_browser_session_token():
    chrome_profile_directory = CHROME_DIRECTORY
    chrome_options = Options()
    # Use the specified profile directory
    chrome_options.add_argument(f"--user-data-dir={chrome_profile_directory}")
    # Maximize the browser window on start
    chrome_options.add_argument("--start-maximized")
    # Create a Chrome WebDriver instance
    driver = webdriver.Chrome(options=chrome_options)
    # Open a website
    url = "https://darkseas.hubsoft.com/"
    driver.get(url)

    time.sleep(random.uniform(2, 4.2))

    def is_login():
        try:
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "username"))
            )
            return True
        except:
            return False

    def do_login():
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "userNameId"))
            ).send_keys(email)
        except:
            pass
        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "userPasswordId"))
            ).send_keys(password)
            WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "button[class='btn btn-large waves-effect indigo']",
                    )
                )
            ).click()
        except:
            pass

    if not is_login():
        do_login()
    if not is_login():
        print("Some error occured in login!")
        exit(0)
    print("Login successful")
    return driver.get_cookies()[5]["value"]


if __name__ == "__main__":
    try:
        main()
    except:
        traceback.print_exc()
    input("Finished")
