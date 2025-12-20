import streamlit as st
import pandas as pd
import asyncio
import time
import math
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from src.models import Car
from src.config import settings

# --- КОНФІГУРАЦІЯ ТА БД ---
KYIV_TZ = ZoneInfo("Europe/Kyiv")

st.set_page_config(page_title="AutoRia Моніторинг", layout="wide")
st.title("🚗 AutoRia: Моніторинг у реальному часі")

engine = create_async_engine(
    settings.DATABASE_URL_asyncpg,
    poolclass=NullPool,
    echo=False,
    isolation_level="AUTOCOMMIT"
)
local_session_factory = async_sessionmaker(engine, expire_on_commit=False)


# --- ФУНКЦІЇ ЗАПИТІВ ---
async def get_total_count():
    async with local_session_factory() as session:
        query = select(func.count(Car.id))
        result = await session.execute(query)
        return result.scalar()


async def get_chart_data():
    async with local_session_factory() as session:
        query = select(Car.price_usd,
                       Car.odometer,
                       Car.title,
                       Car.datetime_found)
        result = await session.execute(query)
        return result.all()


async def get_table_page(offset_val, limit_val):
    async with local_session_factory() as session:
        query = select(Car).order_by(
            desc(Car.id)
        ).offset(offset_val).limit(limit_val)
        result = await session.execute(query)
        cars = result.scalars().all()
        return [
            {k: v for k, v in car.__dict__.items()
             if k != "_sa_instance_state"}
            for car in cars
        ]


def run_sync(coroutine):
    return asyncio.run(coroutine)


# --- САЙДБАР: НАЛАШТУВАННЯ ТА ПАГІНАЦІЯ ---
st.sidebar.header("Налаштування")

try:
    total_items = run_sync(get_total_count())
except Exception as e:
    st.error(f"Помилка підключення: {e}")
    total_items = 0

PAGE_SIZE = 100
if total_items > 0:
    total_pages = math.ceil(total_items / PAGE_SIZE)
else:
    total_pages = 1

page_options = []
for i in range(total_pages):
    start = i * PAGE_SIZE + 1
    end = min((i + 1) * PAGE_SIZE, total_items)
    page_options.append(f"{start}-{end}")

selected_range = st.sidebar.selectbox(
    f"Сторінка (Всього авто: {total_items}):",
    page_options,
    index=0
)

selected_index = page_options.index(selected_range)
offset = selected_index * PAGE_SIZE

st.sidebar.subheader("Відображення таблиці")
show_images = st.sidebar.checkbox("Показувати фото", value=True)

column_mapping = {
    "Пробіг": "odometer",
    "Продавець": "username",
    "Телефон": "phone_number",
    "Держ. номер": "car_number",
    "VIN-код": "car_vin",
    "Час парсингу": "datetime_found"
}

default_cols = ["Пробіг", "Телефон", "Час парсингу"]

selected_columns_labels = st.sidebar.multiselect(
    "Додаткові колонки:",
    options=list(column_mapping.keys()),
    default=default_cols
)

refresh_seconds = st.sidebar.selectbox(
    "Оновлювати кожні (сек):",
    options=[5, 10, 30, 60],
    index=0
)

current_time_kyiv = datetime.now(KYIV_TZ).strftime("%H:%M:%S")
st.caption(f"Стан на: **{current_time_kyiv}** (Київ). "
           f"Наступне оновлення через {refresh_seconds} сек.")

# --- ЗАВАНТАЖЕННЯ ДАНИХ ---
try:
    raw_chart_data = run_sync(get_chart_data())
    df_global = pd.DataFrame(raw_chart_data, columns=['price_usd',
                                                      'odometer',
                                                      'title',
                                                      'datetime_found'])

    table_data = run_sync(get_table_page(offset, PAGE_SIZE))
    df_table = pd.DataFrame(table_data)

except Exception as e:
    st.error(f"Помилка завантаження даних: {e}")
    df_global = pd.DataFrame()
    df_table = pd.DataFrame()

# --- БЛОК: ГЛОБАЛЬНА СТАТИСТИКА ---
st.markdown("### 📊 Глобальна статистика ринку")
if not df_global.empty:
    gm1, gm2, gm3, gm4 = st.columns(4)

    gm1.metric("Всього зібрано", f"{len(df_global):,}")
    gm2.metric("Середня ціна", f"${df_global['price_usd'].mean():,.0f}")
    gm3.metric("Середній пробіг", f"{df_global['odometer'].mean():,.0f} км")

    if df_global['datetime_found'].dt.tz is None:
        df_global['datetime_found'] = pd.to_datetime(
            df_global['datetime_found']
        ).dt.tz_localize('UTC').dt.tz_convert(
            KYIV_TZ)
    else:
        df_global['datetime_found'] = df_global['datetime_found'].dt.tz_convert(
            KYIV_TZ
        )

    last_global_time = df_global['datetime_found'].max().strftime('%H:%M:%S')
    gm4.metric("Останнє авто додано о", last_global_time)

    df_global['Brand'] = df_global['title'].apply(
        lambda x: x.split()[0] if x else "Інше"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.info("Топ марок (аналіз всієї бази)")
        st.bar_chart(df_global['Brand'].value_counts().head(15),
                     color="#FF4B4B")

    with c2:
        st.info("Розподіл цін та пробігів (всі авто)")
        st.scatter_chart(df_global,
                         x='odometer',
                         y='price_usd',
                         color='Brand',
                         size=60)

    # --- БЛОК: ДИНАМІЧНИЙ АНАЛІЗ ---
    st.markdown("---")
    st.markdown("### 🔍 Детальний аналіз по марці")

    all_brands = sorted(df_global['Brand'].unique())

    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        selected_brand = st.selectbox("Оберіть марку авто:", all_brands)

    df_brand = df_global[df_global['Brand'] == selected_brand]

    if not df_brand.empty:
        bm1, bm2, bm3 = st.columns(3)
        bm1.metric(f"Кількість {selected_brand}", len(df_brand))

        avg_price_brand = df_brand['price_usd'].mean()
        avg_price_diff = avg_price_brand - df_global['price_usd'].mean()
        bm2.metric("Середня ціна", f"${avg_price_brand:,.0f}",
                   delta=f"{avg_price_diff:,.0f} від ринку")

        avg_odo_brand = df_brand['odometer'].mean()
        bm3.metric("Середній пробіг", f"{avg_odo_brand:,.0f} км")

        bg1, bg2 = st.columns(2)

        with bg1:
            st.caption(f"💰 Розподіл цін (Гістограма) - {selected_brand}")
            try:
                counts, bins = np.histogram(df_brand['price_usd'], bins=15)
                bin_labels = [f"${int(b / 1000)}k" for b in bins[:-1]]
                chart_data = pd.DataFrame({"Count": counts}, index=bin_labels)
                st.bar_chart(chart_data)
            except Exception:
                st.info("Мало даних для гістограми")

        with bg2:
            st.caption(f"📈 Ціна vs Пробіг - {selected_brand}")
            st.scatter_chart(df_brand, x='odometer', y='price_usd', size=100)
    else:
        st.info("Немає даних по обраній марці.")

else:
    st.warning("Немає даних для статистики.")

st.markdown("---")

# --- БЛОК: ТАБЛИЦЯ ---
st.markdown(f"### 📋 Список авто: {selected_range}")

if not df_table.empty:
    if df_table['datetime_found'].dt.tz is None:
        df_table['datetime_found'] = pd.to_datetime(
            df_table['datetime_found']
        ).dt.tz_localize('UTC').dt.tz_convert(
            KYIV_TZ)
    else:
        df_table['datetime_found'] = df_table['datetime_found'].dt.tz_convert(
            KYIV_TZ
        )

    display_cols = ['id']

    if show_images:
        display_cols.append('image_url')

    display_cols.extend(['title', 'price_usd'])

    for label in selected_columns_labels:
        display_cols.append(column_mapping[label])

    display_cols.append('url')

    column_config = {
        "id": st.column_config.NumberColumn("ID", format="%d"),
        "title": st.column_config.TextColumn("Назва авто"),
        "price_usd": st.column_config.NumberColumn("Ціна ($)", format="$%d"),
        "odometer": st.column_config.NumberColumn("Пробіг", format="%d км"),
        "username": st.column_config.TextColumn("Продавець"),
        "phone_number": st.column_config.NumberColumn("Телефон", format="%d"),
        "car_number": st.column_config.TextColumn("Держ. номер"),
        "car_vin": st.column_config.TextColumn("VIN-код"),
        "datetime_found": st.column_config.DatetimeColumn("Час (Київ)",
                                                          format="HH:mm:ss"),
        "url": st.column_config.LinkColumn("Лінк", display_text="Відкрити"),
    }

    if show_images:
        column_config["image_url"] = st.column_config.ImageColumn("Фото")

    st.dataframe(
        df_table[display_cols],
        column_config=column_config,
        hide_index=True,
    )
else:
    st.warning("На цій сторінці немає даних.")

# --- АВТОМАТИЧНЕ ОНОВЛЕННЯ ---
time.sleep(refresh_seconds)
st.rerun()
