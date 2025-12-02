# Price Tracker - Finnish Electronics Stores

A web application for tracking product prices from Finnish electronics stores (Verkkokauppa.com, Gigantti.fi, and Power.fi). Scrapes prices bi-weekly and provides a searchable UI to view price history.

## Features

- 📊 **Price History Tracking**: Track prices over time for products
- 🔍 **Product Search**: Search across all tracked products
- 📈 **Price Charts**: Visualize price trends with interactive charts
- 🏪 **Multi-Store Support**: Verkkokauppa.com, Gigantti.fi, and Power.fi
- 🔌 **Extensible Architecture**: Easy to add new stores
- 🧹 **Auto Cleanup**: Products without price data are automatically removed

## Architecture

```
├── api/                  # FastAPI backend
│   ├── main.py          # API entry point
│   ├── routes.py        # API endpoints
│   └── schemas.py       # Pydantic models
├── database/             # Database layer
│   ├── models.py        # SQLAlchemy models
│   ├── repository.py    # Data access layer
│   └── session.py       # Database connection
├── scrapers/             # Web scrapers
│   ├── base.py          # Abstract base scraper
│   ├── verkkokauppa.py  # Verkkokauppa.com scraper (API-based)
│   ├── gigantti.py      # Gigantti.fi scraper (API-based)
│   └── power.py         # Power.fi scraper (API-based)
├── frontend/             # React frontend
│   └── src/
│       ├── components/  # React components
│       └── pages/       # Page components
├── scheduler.py          # Bi-weekly scraping scheduler
├── cleanup_db.py         # Database cleanup script
└── run_scraper.py       # Manual scraping script
```

## Setup

### Backend

1. Create a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

3. Create `.env` file (optional):
   ```
   DATABASE_URL=sqlite:///./price_tracker.db
   ```

4. Run the API server:
   ```powershell
   python -m uvicorn api.main:app --reload
   ```

### Frontend

1. Install Node.js dependencies:
   ```powershell
   cd frontend
   npm install
   ```

2. Run development server:
   ```powershell
   npm run dev
   ```

3. Open http://localhost:5173 in your browser

## Usage

### Manual Scraping

Run scraper for all stores:
```powershell
python run_scraper.py
```

Run scraper for specific store:
```powershell
python run_scraper.py --store "Verkkokauppa.com"
python run_scraper.py --store "Gigantti"
python run_scraper.py --store "Power"
```

Limit number of products (useful for testing):
```powershell
python run_scraper.py --limit 10
python run_scraper.py --store "Gigantti" --limit 5
```

### Scheduled Scraping

Run the scheduler to automatically scrape on the 1st and 15th of each month at 3:00 AM:
```powershell
python scheduler.py
```

### API Endpoints

**Stores:**
- `GET /api/stores` - List all active stores
- `GET /api/stores/{id}` - Get store by ID

**Products:**
- `GET /api/products` - List all products (paginated, optional `store_id` filter)
- `GET /api/products/search?q=<query>` - Search products by name
- `GET /api/products/{id}` - Get product details with full price history
- `GET /api/products/{id}/history` - Get price history only
- `GET /api/products/{id}/statistics` - Get price statistics (min, max, avg, change)

## Adding a New Store

1. Create a new scraper class in `scrapers/`:

```python
from typing import AsyncGenerator, Optional
import httpx
from scrapers.base import BaseScraper, ScrapedProduct, SitemapParser

class NewStoreScraper(BaseScraper):
    STORE_NAME = "New Store"
    BASE_URL = "https://newstore.fi"
    SITEMAP_URL = "https://newstore.fi/sitemap.xml"
    API_URL = "https://newstore.fi/api/products"
    
    async def get_product_urls(self) -> AsyncGenerator[str, None]:
        """Get product URLs from sitemap."""
        urls = await SitemapParser.get_urls_from_sitemap(
            self.SITEMAP_URL,
            url_filter='/product/'
        )
        for url in urls:
            yield url
    
    async def scrape_all_products(self) -> AsyncGenerator[ScrapedProduct, None]:
        """Scrape all products using the store's API."""
        async with httpx.AsyncClient() as client:
            async for url in self.get_product_urls():
                product_id = self.extract_product_id(url)
                response = await client.get(f"{self.API_URL}/{product_id}")
                if response.status_code == 200:
                    data = response.json()
                    yield ScrapedProduct(
                        external_id=product_id,
                        name=data['name'],
                        url=url,
                        price=float(data['price']),
                        original_price=data.get('original_price'),
                        brand=data.get('brand'),
                        image_url=data.get('image'),
                        is_available=data.get('in_stock', True)
                    )
    
    @staticmethod
    def extract_product_id(url: str) -> Optional[str]:
        """Extract product ID from URL."""
        import re
        match = re.search(r'/product/(\d+)', url)
        return match.group(1) if match else None
```

2. Register in `scrapers/__init__.py`
3. Add to `SCRAPER_REGISTRY` in `scheduler.py`
4. Add store to database (done automatically on first run)

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, httpx (API-based scraping)
- **Frontend**: React, TypeScript, Vite, Recharts
- **Database**: SQLite (easily switchable to PostgreSQL)
- **Scheduling**: APScheduler

## Deployment (Hetzner Cloud)

### Prerequisites
- Hetzner Cloud VPS (CX23 in Helsinki ~€3.49/month recommended)
- SSH key for authentication
- Domain name (optional)

### Setup SSH Key (for private repos)

If your repository is private, set up SSH access first:

1. Generate an SSH key on your VPS:
   ```bash
   ssh-keygen -t ed25519 -C "your-email@example.com"
   cat ~/.ssh/id_ed25519.pub
   ```

2. Add the public key to GitHub:
   - Go to GitHub → Settings → SSH and GPG keys → New SSH key
   - Paste the public key and save

3. Test the connection:
   ```bash
   ssh -T git@github.com
   ```

### Quick Deploy

1. SSH into your VPS:
   ```bash
   ssh root@your-server-ip
   ```

2. Run the deployment script:
   ```bash
   curl -sSL https://raw.githubusercontent.com/Kasperit/Price-Tracker/main/deploy.sh | bash
   ```

   Or manually:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | bash
   
   # Clone and run (use SSH URL for private repos)
   git clone git@github.com:Kasperit/Price-Tracker.git
   cd Price-Tracker
   docker compose up -d --build
   ```

3. Access your app at `http://your-server-ip`

### Updating the Application

After making changes and pushing to GitHub:

```bash
cd ~/price-tracker
git pull
docker compose up -d --build
```

### Management Commands

```bash
# View logs
docker compose logs -f

# View scraper logs
docker logs -f price-tracker-scheduler-1

# Restart services
docker compose restart

# Run manual scrape
docker compose exec web python run_scraper.py

# Run manual scrape with limit (for testing)
docker compose exec web python run_scraper.py --limit 10

# Cleanup products without prices
docker compose exec web python cleanup_db.py

# Check product count
docker compose exec web python -c "from database.session import SessionLocal; from database.models import Product; db = SessionLocal(); print('Products:', db.query(Product).count())"

# Backup database
cp data/price_tracker.db ~/backups/backup_$(date +%Y%m%d).db
```

### SSL/HTTPS (Optional)

For HTTPS, add Caddy as a reverse proxy:

```bash
# Install Caddy
sudo apt install -y caddy

# Edit Caddyfile
echo "yourdomain.com {
    reverse_proxy localhost:80
}" | sudo tee /etc/caddy/Caddyfile

sudo systemctl restart caddy
```

## License

MIT
