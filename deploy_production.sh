#!/bin/bash
# Indeed Integration Production Deployment Script

# 1. Production Server Setup
echo "=== Indeed Integration Production Deployment ==="

# Clone the app to production
echo "1. Cloning Indeed integration to production..."
# git clone https://github.com/yourusername/indeed-integration.git /path/to/production/frappe-bench/apps/indeed

# Install on production site
echo "2. Installing Indeed app on production site..."
# bench --site production.yoursite.com install-app indeed

# Run migrations
echo "3. Running database migrations..."
# bench --site production.yoursite.com migrate

# Set production settings
echo "4. Configuring production settings..."
# Update Indeed Integration Settings with:
# - Real company name
# - Production domain URLs
# - Strong webhook secret
# - Real contact email

# Restart production
echo "5. Restarting production server..."
# bench restart

echo "✅ Deployment complete!"
echo "Next: Configure production settings in ERPNext"