import asyncio
import json
import os
import re

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from sqlalchemy.dialects.postgresql import insert

from src.database import async_session_factory, init_db
from src.models import Car

sem = asyncio.Semaphore(2)

load_dotenv()

BASE_URL = os.getenv('SITE_URL')


def clean_price(text):
    return int(re.sub(r"[^\d]", "", text))


def clean_odometer(text):
    if not text:
        return 0
    clean_text = re.sub(r"[^\d]", "", text)
    if not clean_text:
        return 0

    digits = int(clean_text)
    if "тис" in text:
        return digits * 1000
    return digits


def get_user_phone_id(soup, car_url):
    script_tag = soup.find("script", string=re.compile("window.__PINIA__"))
    auto_id = car_url.replace(".html", "").split("_")[-1]

    if script_tag:
        script_content = script_tag.string

        json_text = script_content.split('window.__PINIA__ =')[1].strip()
        if json_text.endswith(';'):
            json_text = json_text[:-1]

        try:
            data = json.loads(json_text)

            page_structures = list(data['page']['structures'].values())[0]

            phone_data = page_structures.get('additionalParams', {}).get(
                'phone', {}
            ).get('data', [])

            found_phone_id = None
            found_user_id = None

            for item in phone_data:
                if item[0] == 'phoneId':
                    found_phone_id = item[1]
                elif item[0] == 'userId':
                    found_user_id = item[1]

            return {
                'found_phone_id': found_phone_id,
                'found_user_id': found_user_id,
                'found_auto_id': auto_id
            }
        except Exception:
            return None


def get_phone_number(soup, cookie, car_url):
    data = get_user_phone_id(soup, car_url)

    url = "https://auto.ria.com/bff/final-page/public/auto/popUp"

    payload = {
        "blockId": "autoPhone",
        "popUpId": "autoPhone",
        "isLoginRequired": False,
        "isConfirmPhoneEmailRequired": False,
        "autoId": data["found_auto_id"],
        "params": {
            "userId": data["found_user_id"],
            "phoneId": data["found_phone_id"]
        }
    }
    headers = {
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "no-cache",
        "content-type": "application/json",
        "Cookie": cookie
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    try:
        data = json.loads(response.text)

        raw_phone = data.get("additionalParams", {}).get("phoneStr")

        if raw_phone:

            clean_phone = re.sub(r"[^\d]", "", raw_phone)
            if clean_phone.startswith("0"):
                formatted_phone = "38" + clean_phone
            elif clean_phone.startswith("380"):
                formatted_phone = clean_phone
            else:
                formatted_phone = "380" + clean_phone
            return formatted_phone
        else:
            return None

    except Exception:
        return None


async def save_cars_to_db(cars_data):
    if not cars_data:
        return

    async with async_session_factory() as session:
        stmt = insert(Car).values(cars_data)

        stmt = stmt.on_conflict_do_nothing(index_elements=['url'])

        await session.execute(stmt)
        await session.commit()
        print(f"Збережено нові записи: {len(cars_data)}")


async def fetch_html(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text(encoding='utf-8', errors='replace')


def parse_listing_page(soup):
    links = []
    for item in soup.select("section.ticket-item"):
        ad_type = item.get("data-advertisement-type")
        sold_out_status = item.select_one(".sold-out")
        if ad_type == "NewAuto" or sold_out_status:
            continue
        link_tag = item.select_one("a.m-link-ticket")
        if link_tag and link_tag.get("href"):
            links.append(link_tag["href"])
    return links


async def fetch_car_details(session, car_url):
    async with sem:
        async with session.get(car_url) as response:
            raw_cookie_header = response.headers.get("Set-Cookie")
        html = await fetch_html(session, car_url)
        soup = BeautifulSoup(html, "html.parser")
        cookie = raw_cookie_header

        title = soup.select_one("#sideTitleTitle span").get_text()
        price_tag = soup.select_one("#sidePrice strong")
        image_url = soup.select_one(
            "#photoSlider .picture img"
        ).get("data-src")
        image_count_full = soup.select_one(
            "#photoSlider .common-badge"
        ).find_all("span")
        images_count = image_count_full[1].text
        car_numb_str = soup.select_one(".car-number")
        car_number = car_numb_str.get_text() if car_numb_str else "Відсутній"
        car_vin_str = soup.select_one("#badgesVinGrid .badge-template")
        car_warning_mvs = soup.select_one("#mvs #mvsWarningTitle .titleS")

        if car_vin_str:
            car_vin = soup.select_one(
                "#badgesVinGrid .badge-template"
            ).get_text()
        elif car_warning_mvs:
            car_vin = car_warning_mvs.get_text().split()[-1]
        else:
            car_vin = "Відсутній"
        phone_number = get_phone_number(soup, cookie, car_url)
        if not price_tag:
            price_tag = ""
        price_usd = clean_price(price_tag.get_text(strip=True))
        odo_tag = soup.select_one("#basicInfoTableMainInfo0 span")
        if odo_tag:
            odometer_text = odo_tag.get_text(strip=True)
            odometer = clean_odometer(odometer_text)
        else:
            odometer = 0
        username = soup.select_one(
            "#sellerInfoUserName span.titleM"
        ).get_text()

        data = {
            "url": car_url,
            'title': title,
            "price_usd": price_usd,
            "odometer": odometer,
            "username": username,
            "phone_number": int(phone_number),
            "image_url": image_url,
            "images_count": int(images_count),
            "car_number": car_number,
            "car_vin": car_vin
        }
        return data


async def parse_page(session, page):
    url = f"{BASE_URL}?page={page}"
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")

    car_links = parse_listing_page(soup)
    if not car_links:
        print('car_links', car_links)
        return None, None

    tasks = [fetch_car_details(session, link) for link in car_links]
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r is not None]

    next_btn = soup.select_one("a.js-next")
    has_next = next_btn and "disabled" not in next_btn.get("class", [])
    print('has_next', has_next)
    return results, has_next


async def main():
    await init_db()
    headers = {"User-Agent": "Mozilla/5.0"}
    page = 1

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            results, has_next = await parse_page(session, page)

            if results:
                await save_cars_to_db(results)

            if not has_next:
                print("Finish.")
                break

            page += 1
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
