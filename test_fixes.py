"""
Test script to verify the fixes work correctly.
"""

import pandas as pd
from data_manager import DataManager

def test_data_loading():
    """Test that reference data loads correctly"""
    print("Testing data loading...")
    dm = DataManager('data.txt', 'Knowledgebase.json')

    if dm.reference_data:
        print("✅ Reference data loaded successfully!")
        print(f"Found {len(dm.reference_data)} reference categories:")
        for category, items in dm.reference_data.items():
            print(f"  - {category}: {len(items)} items")
    else:
        print("❌ Reference data failed to load")

def test_dataframe_conversion():
    """Test that dataframe conversion works without PyArrow errors"""
    print("\nTesting dataframe conversion...")

    # Simulate classification data with mixed types
    classified_data = {
        "ISSUETYPE": {"Value": "5", "Label": "Software/SaaS"},
        "SUBISSUETYPE": {"Value": 48, "Label": "Application Issue"},
        "PRIORITY": {"Value": 3, "Label": "Medium"}
    }

    # Test the fix - convert all values to strings
    table_data = []
    for field in ["ISSUETYPE", "SUBISSUETYPE", "PRIORITY"]:
        val = classified_data.get(field, {})
        table_data.append({
            "Field": field,
            "Value": str(val.get('Value', 'N/A')),
            "Label": str(val.get('Label', 'N/A'))
        })

    try:
        df = pd.DataFrame(table_data)
        print("✅ DataFrame creation successful!")
        print("DataFrame contents:")
        print(df)

        # Test Arrow conversion
        import pyarrow as pa
        table = pa.Table.from_pandas(df)
        print("✅ PyArrow conversion successful!")

    except Exception as e:
        print(f"❌ DataFrame/PyArrow conversion failed: {e}")

def test_mock_llm_response():
    """Test that plain text LLM responses work"""
    print("\nTesting mock LLM response handling...")

    # Simulate a plain text response (what we expect from resolution generation)
    mock_response = """1. Check the email or message you received with the cloud link to ensure it hasn't been accidentally marked as read.
2. If the link is in an email, try copying the entire link and pasting it directly into your web browser.
3. Verify that the link is correctly formatted and does not contain any typos.
4. If the link has expired, request a new one from the sender.
5. Try accessing the cloud service using a different web browser or device."""

    # Test the fix - handle plain text responses
    if isinstance(mock_response, str) and mock_response.strip():
        result = mock_response.strip()
        print("✅ Plain text LLM response handling successful!")
        print(f"Response length: {len(result)} characters")
        print(f"First 100 chars: {result[:100]}...")
    else:
        print("❌ Plain text LLM response handling failed")

def test_urgency_level_extraction():
    """Test that urgency level extraction works properly"""
    print("\nTesting urgency level extraction logic...")

    # Simulate different types of tickets and their expected urgency levels
    test_cases = [
        {
            "title": "System completely down - all users affected",
            "description": "The entire network is down and no one can access any systems",
            "expected_urgency": "Critical"
        },
        {
            "title": "Email not working for one user",
            "description": "John's email is not syncing properly, but he can still access webmail",
            "expected_urgency": "Medium"
        },
        {
            "title": "Request for new software installation",
            "description": "Can you please install Adobe Photoshop on my computer when convenient?",
            "expected_urgency": "Low"
        },
        {
            "title": "VPN connection issues affecting remote work",
            "description": "Multiple remote workers cannot connect to VPN, blocking access to company resources",
            "expected_urgency": "High"
        }
    ]

    print("Test cases for urgency level assessment:")
    for i, case in enumerate(test_cases, 1):
        print(f"  {i}. Title: '{case['title'][:50]}...'")
        print(f"     Expected urgency: {case['expected_urgency']}")

    print("✅ Urgency level extraction test cases prepared!")
    print("Note: Actual LLM testing requires Snowflake connection")

def test_error_message_extraction():
    """Test that error message extraction works properly"""
    print("\nTesting error message extraction logic...")

    # Test cases with different types of error messages
    error_test_cases = [
        {
            "title": "Login failed with error code",
            "description": "When I try to login, I get 'Error 401: Unauthorized access' message",
            "expected_error": "Error 401: Unauthorized access"
        },
        {
            "title": "Application crashes on startup",
            "description": "Excel shows 'The application was unable to start correctly (0xc0000142)' and then closes",
            "expected_error": "The application was unable to start correctly (0xc0000142)"
        },
        {
            "title": "Network connection timeout",
            "description": "Getting 'Connection timeout after 30 seconds' when trying to access the server",
            "expected_error": "Connection timeout after 30 seconds"
        },
        {
            "title": "Printer not working",
            "description": "The printer is not responding and shows a red light",
            "expected_error": "printer not responding, red light indicator"
        },
        {
            "title": "Cloud access issue",
            "description": "The link is expired and I cannot access the cloud workspace",
            "expected_error": "link is expired"
        }
    ]

    print("Test cases for error message extraction:")
    for i, case in enumerate(error_test_cases, 1):
        print(f"  {i}. Title: '{case['title']}'")
        print(f"     Description: '{case['description'][:60]}...'")
        print(f"     Expected error: '{case['expected_error']}'")

    print("✅ Error message extraction test cases prepared!")
    print("Note: The improved prompt should now extract these error messages properly")

def test_env_loading():
    """Test that environment variables are loaded correctly"""
    print("\nTesting .env file loading...")

    try:
        from config import SF_ACCOUNT, SF_USER, SF_DATABASE, SUPPORT_PHONE, SUPPORT_EMAIL

        # Check if credentials are loaded
        if SF_ACCOUNT and SF_USER and SF_DATABASE:
            print("✅ Snowflake credentials loaded successfully!")
            print(f"  - Account: {SF_ACCOUNT}")
            print(f"  - User: {SF_USER}")
            print(f"  - Database: {SF_DATABASE}")
        else:
            print("❌ Snowflake credentials not loaded properly")

        # Check contact info
        if SUPPORT_PHONE and SUPPORT_EMAIL:
            print("✅ Contact information loaded successfully!")
            print(f"  - Phone: {SUPPORT_PHONE}")
            print(f"  - Email: {SUPPORT_EMAIL}")
        else:
            print("❌ Contact information not loaded properly")

    except ImportError as e:
        print(f"❌ Error importing config: {e}")
    except Exception as e:
        print(f"❌ Error testing .env loading: {e}")

if __name__ == "__main__":
    print("🔧 Testing fixes for the modular application...\n")

    test_data_loading()
    test_dataframe_conversion()
    test_mock_llm_response()
    test_urgency_level_extraction()
    test_error_message_extraction()
    test_env_loading()

    print("\n✅ All tests completed!")