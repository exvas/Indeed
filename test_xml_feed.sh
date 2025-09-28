#!/bin/bash

# ERPNext Indeed XML Feed Test Script
# Run this from your frappe-bench directory

echo "🧪 Indeed XML Feed Integration Tester"
echo "====================================="

# Check if we're in the right directory
if [ ! -d "apps" ] || [ ! -f "bench" ]; then
    echo "❌ Error: Run this script from frappe-bench directory"
    exit 1
fi

# Get site name
if [ -z "$1" ]; then
    echo "Usage: $0 <site-name>"
    echo "Example: $0 mysite.local"
    exit 1
fi

SITE=$1
echo "🌐 Testing site: $SITE"

# Test 1: Check if app is installed
echo ""
echo "📦 Checking app installation..."
if bench --site $SITE list-apps | grep -q "indeed"; then
    echo "✅ Indeed app is installed"
else
    echo "❌ Indeed app not found. Install it first:"
    echo "   bench --site $SITE install-app indeed"
    exit 1
fi

# Test 2: Check XML feed accessibility
echo ""
echo "🌐 Testing XML feed accessibility..."
SITE_URL=$(bench --site $SITE execute "print(frappe.utils.get_url())")
FEED_URL="$SITE_URL/files/indeed_jobs.xml"

echo "   Feed URL: $FEED_URL"

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FEED_URL")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ XML feed is accessible (HTTP 200)"
    
    # Check if it's valid XML
    CONTENT=$(curl -s "$FEED_URL")
    if echo "$CONTENT" | xmllint --noout - 2>/dev/null; then
        echo "✅ XML feed has valid syntax"
        
        # Count jobs in feed
        JOB_COUNT=$(echo "$CONTENT" | grep -c "<job>")
        echo "📊 Found $JOB_COUNT jobs in feed"
        
        if [ $JOB_COUNT -gt 0 ]; then
            echo "✅ XML feed contains job data"
        else
            echo "⚠️  XML feed is empty (no jobs found)"
        fi
    else
        echo "❌ XML feed has invalid syntax"
    fi
else
    echo "❌ XML feed not accessible (HTTP $HTTP_STATUS)"
    echo "   This might be normal if no jobs have been posted yet"
fi

# Test 3: Check integration settings
echo ""
echo "⚙️  Checking integration settings..."
SETTINGS_CHECK=$(bench --site $SITE execute "
try:
    settings = frappe.get_single('Indeed Integration Settings')
    print(f'Method: {settings.integration_method}')
    print(f'Auto-posting: {settings.enable_auto_posting}')
    print(f'Company: {settings.company or \"Not set\"}')
except Exception as e:
    print(f'Error: {e}')
")
echo "$SETTINGS_CHECK"

# Test 4: Run quick API test
echo ""
echo "🔧 Running API quick test..."
API_TEST=$(bench --site $SITE execute "
try:
    result = frappe.call('indeed.indeed.api.test_xml_feed_quick')
    if result.get('success'):
        print('✅ API Test: SUCCESS')
        print(f'   Message: {result.get(\"message\")}')
        print(f'   Feed URL: {result.get(\"feed_url\")}')
    else:
        print('❌ API Test: FAILED')
        print(f'   Message: {result.get(\"message\")}')
except Exception as e:
    print(f'❌ API Test Error: {e}')
")
echo "$API_TEST"

# Test 5: Create test job (optional)
echo ""
read -p "🆕 Create a test job for testing? (y/N): " CREATE_TEST
if [[ $CREATE_TEST =~ ^[Yy]$ ]]; then
    echo "Creating test job..."
    TEST_JOB=$(bench --site $SITE execute "
try:
    result = frappe.call('indeed.indeed.api.create_test_job')
    if result.get('success'):
        print('✅ Test job created successfully')
        print(f'   Job Name: {result.get(\"job_name\")}')
        print(f'   Job Title: {result.get(\"job_title\")}')
        if result.get('integration'):
            print(f'   Integration Status: {result.get(\"integration\", {}).get(\"status\", \"Unknown\")}')
    else:
        print('❌ Failed to create test job')
        print(f'   Error: {result.get(\"message\")}')
except Exception as e:
    print(f'❌ Test job creation error: {e}')
")
    echo "$TEST_JOB"
    
    # Regenerate feed after creating test job
    echo ""
    echo "🔄 Regenerating XML feed..."
    REGEN_RESULT=$(bench --site $SITE execute "
try:
    result = frappe.call('indeed.indeed.api.regenerate_indeed_xml_feed')
    if result.get('success'):
        print('✅ XML feed regenerated successfully')
        print(f'   Message: {result.get(\"message\")}')
    else:
        print('❌ XML feed regeneration failed')
        print(f'   Error: {result.get(\"error\")}')
except Exception as e:
    print(f'❌ Regeneration error: {e}')
")
    echo "$REGEN_RESULT"
fi

# Summary
echo ""
echo "📋 Test Summary"
echo "==============="
echo "✅ = Working correctly"
echo "⚠️  = Needs attention"
echo "❌ = Requires fixing"
echo ""
echo "Next steps:"
echo "1. Configure Indeed Integration Settings if not done"
echo "2. Create Job Openings with 'Post to Indeed' checked"
echo "3. Submit feed URL to Indeed: $FEED_URL"
echo "4. Monitor for Indeed crawler access in web server logs"
echo ""
echo "📚 For detailed instructions, see XML_FEED_TESTING.md"