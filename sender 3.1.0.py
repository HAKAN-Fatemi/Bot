import requests
import os
from dotenv import load_dotenv
import time
import base64
from threading import Timer
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re

load_dotenv()

# API
MEYDOONY_API_URL = "https://meydoony.ir/uniq/api"
MEYDOONY_API_KEY = os.getenv("MEYDOONY_API_KEY")
BALE_TOKEN = os.getenv("BALE_TOKEN")
BALE_CHANNEL = os.getenv("BALE_CHANNEL")

if not BALE_TOKEN or not BALE_CHANNEL:
    print("eror: BALE_TOKEN or BALE_CHANNEL")
    exit()

BALE_BASE_URL = f"https://tapi.bale.ai/bot{BALE_TOKEN}"
sent_ad_ids = set()
FILE_HISTORY = "file_history.txt"

USE_DELAYED_SAVE = False # True = با تأخیر | False = فوری
PENDING_SAVE = False
SAVE_DELAY = 5

def create_session(retries=3, backoff_factor=0.5):
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

session = create_session()

def schedule_save():
    global PENDING_SAVE
    if not PENDING_SAVE:
        PENDING_SAVE = True
        Timer(SAVE_DELAY, save_sent_ids).start()

def add_emoji_to_text(text):
    emoji_map = {
        "زمینی": "🥔", "سیب": "🍏", "گلابی": "🍐", "پرتقال": "🍊", "لیمو": "🍋", "طالبی": "🍈",
        "خربزه": "🍈", "هندوانه": "🍉", "انگور": "🍇", "شاه": "🍇", "توت‌فرنگی": "🍓", "توت": "🍓", 
        "شاه‌توت": "🍓", "گیلاس": "🍒", "آلبالو": "🍒", "هلو": "🍑", "شلیل": "🍑", "زردآلو": "🍑", 
        "زردآلو": "🍑", "آناناس": "🍍", "انبه": "🥭", "موز": "🍌", "کیوی": "🥝", "گوجه": "🍅", "گوجه‌فرنگی": "🍅", 
        "نارگیل": "🥥", "آووکادو": "🥑", "زیتون": "🫒", "بلوبری": "🫐", "تمشک": "🫐", "خرما": "🌴", "گردو": "🌰", 
        "بادام": "🌰", "پسته": "🌰", "فندق": "🌰", "خرنوب": "🌰", "کلم بروکلی": "🥦", "کلم‌بروکلی": "🥦", 
        "کاهو": "🥬", "خیار": "🥒", "هویج": "🥕", "سیر": "🧄", "پیاز": "🧅", "تره‌": "🧅", "تره‌فرنگی": "🧅", 
        "سیب‌زمینی": "🥔", "شیرین": "🍠", "بادمجان": "🍆", "قارچ": "🍄", "دلمه": "🫑", "دلمه‌ای": "🫑", 
        "فلفل تند": "🌶", "فلفل": "🌶", "ذرت": "🌽", "نخود": "🫛", "نخود‌فرنگی": "🫛", "لوبیا": "🫛", "لوبیاسبز": "🫛", 
        "کلم": "🥬", "گل": "🌹", "کرفس": "🥬", "زنجبیل": "🫚", "زردچوبه": "🫚", "زرد": "🫚", "نعناع": "🌿", 
        "جعفری": "🌿", "گشنیز": "🌿", "ریحان": "🌿", "شوید": "🌿", "برنج": "🍚", "گندم": "🌾", "جو": "🌾", 
        "چــاودار": "🌾", "جو": "🌾", "ارزن": "🌾", "سورگوم": "🌾", "عدس": "🫘", "نخود": "🫘", "لوبیا": "🫘", 
        "ماش": "🫘", "باقلا": "🫘", "باقله": "🫘", "آفتابگردان": "🌻", "آفتابگردون": "🌻", "نیشکر": "🍬", 
        "چغندرقند": "🍬", "چغندر": "🍬", "قهوه": "☕", "کاکائو": "🍫", "کلزا": "🌱", "سویا": "🌱", 
        "کنجد": "🌱", "کتان": "🌱", "پنبه": "🌱"}
    
    pattern = re.compile(
        r'\b(?:' + '|'.join(re.escape(kw) for kw in emoji_map.keys()) + r')\b',
        re.IGNORECASE)
    
    match = pattern.search(text)
    if match:
        return f"{emoji_map[match.group()]} {text}"
    return f"🍏 {text}"

def get_new_ads(limit=10):
    try:
        response = session.post(
            f"{MEYDOONY_API_URL}?limit={limit}&api={MEYDOONY_API_KEY}",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        if data.get("success"):
            return data.get("data", [])
        else:
            print(f"Meydoony: {data.get('error', 'eror')}")
            return []
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"eror as server meydony: {e}")
        return []

def send_to_bale(endpoint: str, data=None, files=None):
    """تابع کمکی برای ارسال به Bale با timeout یکسان"""
    url = f"{BALE_BASE_URL}/{endpoint}"
    try:
        if files:
            response = session.post(url, files=files, data=data, timeout=15)
        else:
            response = session.post(url, json=data, timeout=15)
        response.raise_for_status()
        result = response.json()
        if result.get("ok"):
            return result.get("result", {}).get("message_id")
        else:
            print(f"Eror Bale: {result.get('description', 'خطای ناشناخته')}")
            return None
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Eror Bale: {e}")
        return None

def send_message_to_bale(caption: str):
    print("sent text")
    return send_to_bale("sendMessage", {
        "chat_id": BALE_CHANNEL,
        "text": caption,
        "parse_mode": "Markdown"
    })

def send_photo_with_caption_to_bale(photo_base64: str, caption: str):
    try:
        header, encoded = photo_base64.split(",", 1)
        image_data = base64.b64decode(encoded)
    except Exception as e:
        print(f"Eror photos Base64: {e}")
        return None

    files = {"photo": ("photo.webp", image_data, "image/webp")}
    data = {
        "chat_id": BALE_CHANNEL,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    
    result = send_to_bale("sendPhoto", data, files)
    if result:
        return result

def format_ad_message(ad):
    title = ad.get("title", "بدون عنوان")
    price = ad.get("price")
    negotiable = ad.get("isNegotiable", False)
    province = ad.get("province", "نامشخص")
    location = ad.get("location", "نامشخص")
    city = ad.get("city", "نامشخص")
    
    price_str = ""
    if price is not None:
        price_str = f"{price:,}".replace(",", "٬") + " تومان"
        if negotiable:
            price_str += " (توافقی)"
    else:
        price_str += "(توافقی)"


    emoji = add_emoji_to_text(title)
    message = f"*{emoji}*\n\n"
    message += f"*📍 مکان:* {province}، {city}، {location}\n"
    message += f"*💸 قیمت:* {price_str}\n \n"

    description = ad.get("description")
    if description:
        max_desc_len = 200
        if len(description) > max_desc_len:
            description = description[:max_desc_len] + "..."
        message += f"*📝 توضیحات:* {description}\n"
    else:
        message += f"*📝 توضیحات:* ...\n"

    message += f"\n[*(شناسه آگهی: {ad.get('id')})*](https://meydoony.ir/product/{ad.get('id')})\n \n"
    message += f"*🌐 وب سایت:* www.meydoony.ir"
    message += f"\n*🎖️ کانال میدونی:* @meydoony_channel"
    return message

def load_sent_ids():
    global sent_ad_ids
    try:
        with open(FILE_HISTORY, "r") as f:
            sent_ad_ids = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        sent_ad_ids = set()
        with open(FILE_HISTORY, "w") as f:
            pass
        print("Created new sent IDs file")

def save_sent_ids():
    global PENDING_SAVE
    if sent_ad_ids:
        with open(FILE_HISTORY, "w") as f:
            sorted_ids = sorted(sent_ad_ids, key=int)
            f.write("\n".join(sorted_ids))
        print(f"💾 Saved {len(sent_ad_ids)} IDs to file")
    PENDING_SAVE = False

def main_loop():
    print("\n🔍 searching...")
    consecutive_errors = 0
    
    while True:
        try:
            ads = get_new_ads()
            
            if ads:
                print(f"🆔 {len(ads)} new AD")
                consecutive_errors = 0
                
                for ad in reversed(ads):
                    ad_id = ad.get("id")
                    if ad_id and str(ad_id) not in sent_ad_ids:
                        message_text = format_ad_message(ad)
                        main_image_base64 = ad.get("mainImage")

                        sent_successfully = False
                        
                        if main_image_base64 and main_image_base64.startswith("data:image/webp;"):
                            print(f"\n📤 sending file {ad_id}...")
                            sent_message_id = send_photo_with_caption_to_bale(main_image_base64, message_text)
                            if sent_message_id:
                                sent_successfully = True
                        else:
                            print(f"no photos {ad_id}")
                            sent_message_id = send_message_to_bale(message_text)
                            if sent_message_id:
                                sent_successfully = True
                        
                        if sent_successfully:
                            sent_ad_ids.add(str(ad_id))
                            print(f"✅ sent file {ad_id}" )
                            if USE_DELAYED_SAVE:
                                schedule_save()
                            else:
                                save_sent_ids()

                        else:
                            print(f"eror id {ad_id}.")
            else:
                print("not a new AD")
                consecutive_errors += 1

            sleep_time = 100 if consecutive_errors < 3 else min(300, 100 * consecutive_errors)
            print(f"\n⏳hakan fell asleep for {sleep_time}s... \n")
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    if not MEYDOONY_API_KEY:
        print("no API Meydoony")
    load_sent_ids()
    try:
        main_loop()
    finally:
        if PENDING_SAVE:
            save_sent_ids()