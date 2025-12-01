#!/bin/bash
# Hetzner VPS Deployment Script
# Run this on a fresh Ubuntu 22.04 VPS

set -e

echo "=== Price Tracker Deployment ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Create app directory
mkdir -p ~/price-tracker
cd ~/price-tracker

# Clone repository (use SSH for private repos)
# For private repo: git clone git@github.com:Kasperit/Price-Tracker.git .
# For public repo: git clone https://github.com/Kasperit/Price-Tracker.git .
git clone git@github.com:Kasperit/Price-Tracker.git .

# Create data directory for SQLite
mkdir -p data

# Build and start containers
sudo docker compose up -d --build

# Wait for containers to be ready
echo "Waiting for services to start..."
sleep 10

# Only run initial scrape if database is empty (first deployment)
PRODUCT_COUNT=$(sudo docker compose exec -T web python -c "from database.session import SessionLocal, init_db; from database.models import Product; init_db(); db = SessionLocal(); print(db.query(Product).count()); db.close()" 2>/dev/null || echo "0")

if [ "$PRODUCT_COUNT" = "0" ]; then
    echo "Database is empty. Running initial scrape (this may take a while)..."
    sudo docker compose exec -T web python run_scraper.py
    echo "Initial scrape complete!"
else
    echo "Database already has $PRODUCT_COUNT products. Skipping initial scrape."
fi

# Set up automatic database backup (daily to home directory)
(crontab -l 2>/dev/null; echo "0 3 * * * cp ~/price-tracker/data/price_tracker.db ~/backups/price_tracker_\$(date +\%Y\%m\%d).db") | crontab -

# Create backups directory
mkdir -p ~/backups

echo "=== Deployment Complete ==="
echo "App running at: http://$(curl -s ifconfig.me)"
echo ""
echo "Useful commands:"
echo "  View logs:     docker compose logs -f"
echo "  Restart:       docker compose restart"
echo "  Stop:          docker compose down"
echo "  Manual scrape: docker compose exec web python run_scraper.py --limit 10"
