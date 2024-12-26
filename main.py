from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import json
import os
import csv
from concurrent.futures import ThreadPoolExecutor
from itertools import cycle

# Загрузка конфигурации
with open("config.json", "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

max_connection = config["max_connection"]
city = config["city"]
choosen_address = config["address_tt"]
categories_list = config["categories"].split(",")
CHROMEDRIVER_PATH = config["chromedriver_path"]
proxies = config["proxies"]

print(max_connection, city, choosen_address, categories_list)

proxy_cycle = cycle(proxies)

base_url = "https://www.bethowen.ru/catalogue/"
categories = [f"{base_url}{category.strip()}/" for category in categories_list if category.strip()]

# Создание файла CSV, если его нет
file_path = "results.csv"
if not os.path.exists(file_path):
    with open(file_path, mode="w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow([
            "City", "Code", "Name", "Price Retail", "Price Discount", "Address", "Quantity", "Availability"
        ])

# Функция для записи данных в CSV
def save_to_csv(data):
    with open(file_path, mode="a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(data)

# Настройка Selenium
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--headless=new")
options.add_argument("--disable-extensions")
options.add_argument("--no-sandbox")
options.add_argument("--disable-gpu")
options.add_argument("--log-level=3")
options.add_argument("--disable-logging")
options.add_argument("--disable-webrtc")
options.add_argument("--disable-webgl")
options.add_argument("--disable-webgl2")
options.add_argument("--disable-software-rasterizer")
options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.add_argument("--silent")
options.add_argument("--incognito")
options.page_load_strategy = "none"  # Не ждать полной загрузки страницы

service = Service(CHROMEDRIVER_PATH)
service.log_path = "NUL"


# Собираем oid с помощью Selenium
def process_category(category):
    proxy = next(proxy_cycle)
    if proxy!='localhost':
        options.add_argument(f"--proxy-server={proxy}")
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)
    # Открываем сайт со своей задержкой, а не встроенной, чтобы не ждать +100500 лет пока прогрузятся все мусорные элементы
    # хотя кнопка для смены региона уже доступна
    driver.get("https://www.bethowen.ru/123")
    time.sleep(5)

    # Нажатие на кнопку выбора региона
    region_button = wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "ixi-header__top--region-desktop"))
    )


    # Сохраняем текущее значение текста элемента
    initial_text = driver.find_element(By.CLASS_NAME, "ixi-header__top--region-desktop").text

    do_change_city=1
    # При запуске сайт выставляет адрес на основе айпи (если доступ к гео не был дан) и если он уже соответствует
    if initial_text==city:
        do_change_city=0

    region_worked=0

    while do_change_city==1:
        try:
            if region_worked==0:
                region_button.click()
            else:
                break
            city_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input.dgn-city-search-input"))
            )
            region_worked=1
            city_input.send_keys(city)

            # Ожидание появления первого элемента из списка

            while driver.find_element(By.CLASS_NAME, "ixi-header__top--region-desktop").text == initial_text:
                try:
                    # Поиск родительского элемента списка
                    parent_element = driver.find_element(By.CSS_SELECTOR, "div.dgn-flex.dgn-relative.dgn-flex-col.dgn-text-sm")

                    # Поиск первого дочернего элемента списка (по классу, совпадающему с "кликабельным" элементом)
                    first_city_option = parent_element.find_element(By.CSS_SELECTOR, "div.dgn-mb-4 > div.dgn-flex")
                    first_city_option.click()
                except:
                    pass
            break
        except:
            pass

    oids = []
    page = 1
    stop_page = 0
    last_page = 0
    while stop_page == 0:
        print(f'\n\nCurrent page: {page}')
        driver.get(f"{category}?PAGEN_1={page}")

        while True:
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".bth-products-list-container")))
                break
            except:
                pass

        if last_page == 0:
            nums_div = driver.find_element(By.CSS_SELECTOR, ".nums.dgn-pt-6.dgn-pb-16")
            last_page = int(nums_div.find_elements(By.CLASS_NAME, "dark_link")[-1].text)
            print("Last page:", last_page)

        products_container = driver.find_element(By.CSS_SELECTOR, ".bth-products-list-container")
        products = products_container.find_elements(By.CSS_SELECTOR, ".bth-card-element")
        for product in products:
            oid = product.get_attribute("data-product-id")
            print(f'Current oid: {oid}')
            oids.append(oid)

        if page >= last_page:
            stop_page = 1
        page += 1
    driver.quit()
    return oids

# Используем ThreadPoolExecutor для параллельной обработки категорий
with ThreadPoolExecutor(max_workers=max_connection) as executor:
    results = list(executor.map(process_category, categories))

# Объединяем результаты всех категорий
oids = [oid for result in results for oid in result]
print(oids)

# Дальнейшая обработка данных (перемещаем код из первой части)
def process_oid(oid):
    print(f'Parsing {oid}...')
    product_details_url = f"https://www.bethowen.ru/api/local/v1/catalog/products/{oid}/details"
    product_details_response = requests.get(product_details_url)
    if product_details_response.status_code != 200:
        print(f"FAILED PARSING {oid}")
        for i in range(1, 6):
            print(f'attempt {i}')
            product_details_response = requests.get(product_details_url)
            if product_details_response.status_code == 200:
                print(f'Successfully parsed {oid} at {i} attempt')
                break
            time.sleep(5)
    product_details_json = product_details_response.json()
    product_name = product_details_json['name']

    # Товар может быть один, но может иметь разную фасовку, этот цикл отвечает за их обработку
    offers = product_details_json.get("offers", [])
    for offer in offers:
        offer_id = offer["id"]
        offer_details_url = f"https://www.bethowen.ru/api/local/v1/catalog/offers/{offer_id}/details"
        offer_details_response = requests.get(offer_details_url)
        if offer_details_response.status_code != 200:
            print(f'FAILED PARSING {oid} ({offer["id"]})')
            for i in range(1, 6):
                print(f'attempt {i}')
                offer_details_response = requests.get(offer_details_url)
                if offer_details_response.status_code == 200:
                    print(f'Successfully parsed {oid} ({offer["id"]}) at {i} attempt')
                    break
                time.sleep(5)
        offer_details_json = offer_details_response.json()

        availability_info = offer_details_json.get("availability_info", {})
        store_amount = availability_info.get("offer_store_amount", [])

        availability = False
        availability_count = 0
        for item in store_amount:
            if choosen_address in item["address"]:
                availability = True
                availability_count = item["availability"]["text"]
                break

        # Если есть в наличие сохраняем, иначе выдаём в консоль skipped
        if availability:
            vendor_code = offer_details_json.get("vendor_code", "")
            retail_price = offer_details_json.get("retail_price", "")
            discount_price = offer_details_json.get("discount_price", "")
            save_to_csv([
                city, vendor_code, product_name, retail_price, discount_price, choosen_address,
                availability_count, availability
            ])
            print(f'Saved: {oid}')
        else:
            print(f'Skipped (not available in tt): {oid} ({offer["id"]})')

# Используем ThreadPoolExecutor для параллельной обработки oids
with ThreadPoolExecutor(max_workers=max_connection) as executor:
    executor.map(process_oid, oids)
