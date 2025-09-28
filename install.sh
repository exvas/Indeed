#!/bin/bash

# ERPNext Indeed Integration - Installation Script
# Run this script from your frappe-bench directory

echo "🚀 Installing ERPNext Indeed Integration..."

# Check if we're in frappe-bench directory
if [ ! -d "apps" ] || [ ! -f "bench" ]; then
    echo "❌ Error: This script must be run from frappe-bench directory"
    exit 1
fi

# Install the app
echo "📦 Installing Indeed app..."
bench --site all install-app indeed

if [ $? -eq 0 ]; then
    echo "✅ Indeed Integration installed successfully!"
    echo ""
    echo "📋 Next Steps:"
    echo "1. Go to your ERPNext site"
    echo "2. Navigate to Setup > Indeed Integration Settings"
    echo "3. Configure your integration method:"
    echo "   - XML_FEED: For basic integration (recommended)"
    echo "   - API: If you have Indeed Partner access"
    echo "4. Enable 'Auto Posting to Indeed'"
    echo "5. Set your default company and HR contact email"
    echo ""
    echo "🔗 Webhook URL (for receiving applications):"
    echo "   https://your-site.com/api/method/indeed.indeed.utils.indeed_application_webhook"
    echo ""
    echo "📄 XML Feed URL (for Indeed to crawl):"
    echo "   https://your-site.com/files/indeed_jobs.xml"
    echo ""
    echo "📚 Check README_INTEGRATION.md for detailed setup instructions"
else
    echo "❌ Installation failed. Please check the error messages above."
fi