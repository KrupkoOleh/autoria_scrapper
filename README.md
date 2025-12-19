# AutoRia Scraper Bot 🚗

An asynchronous high-performance web scraper designed to monitor car listings on Auto.ria.com.

The project is fully containerized using **Docker** and includes automated database backups.

## 🛠 Tech Stack

* **Language:** Python 3.11
* **Core Libs:** `aiohttp` (Async HTTP), `BeautifulSoup4` (Parsing), `SQLAlchemy` (Async ORM)
* **Database:** PostgreSQL 15
* **Infrastructure:** Docker & Docker Compose
* **Migrations:** Alembic
* **Backups:** Automated daily backups via `pgbackups`

## ✨ Features

* **Asynchronous Scraping:** fast data collection using `asyncio`.
* **Sold Status Tracking:** automatically detects sold cars.
* **Check vin code:** find vin-code at the other block of page to add data.
* **Auto Backups:** scheduled database dumps saved to the local `./dumps` folder.

---

## 🚀 How to Run (Docker)

### 1. Clone the repository
```bash
git clone https://github.com/KrupkoOleh/autoria_scrapper.git
cd autoria_scrapper
```

### 2. Pick up the container
```bash
docker-compose up -d --build
```