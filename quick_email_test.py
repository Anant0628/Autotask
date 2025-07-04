"""
Quick test to verify email configuration and send a real notification.
"""

import os
from dotenv import load_dotenv
from notify_agent import NotifyAgent

# Load environment variables
load_dotenv()

def test_email_config():
    """Test email configuration"""
    print("🔧 Testing Email Configuration")
    print("=" * 40)
    
    # Check environment variables
    notify_user = os.getenv('NOTIFY_EMAIL_USER')
    notify_pass = os.getenv('NOTIFY_EMAIL_PASSWORD')
    
    print(f"NOTIFY_EMAIL_USER: {notify_user}")
    print(f"NOTIFY_EMAIL_PASSWORD: {'*' * len(notify_pass) if notify_pass else 'NOT SET'}")
    
    if not notify_pass:
        print("❌ Email password not found in environment variables")
        return False
    
    print("✅ Email configuration found")
    return True

def send_test_notification():
    """Send a test notification"""
    print("\n📧 Sending Test Notification")
    print("=" * 40)
    
    # Create Notify Agent
    notify_agent = NotifyAgent()
    
    # Test data
    test_data = {
        'ticket_id': 'QUICK-TEST-001',
        'issue': 'Quick test notification',
        'description': 'This is a quick test to verify the Notify Agent can send real emails.',
        'due_date': '2024-01-15',
        'priority': 'Medium',
        'category': 'Test',
        'technician_name': 'Test Technician',
        'technician_email': 'rohankul2017@gmail.com',
        'user_name': 'Test User',
        'user_email': 'rohankul2017@gmail.com'
    }
    
    print("📋 Test Data:")
    print(f"  Ticket ID: {test_data['ticket_id']}")
    print(f"  Technician Email: {test_data['technician_email']}")
    print(f"  User Email: {test_data['user_email']}")
    
    # Send notifications
    print("\n🚀 Sending notifications...")
    results = notify_agent.process_ticket_assignment(test_data)
    
    # Show results
    print("\n📊 Results:")
    print(f"  Technician Notification: {'✅ SUCCESS' if results['technician_notification'] else '❌ FAILED'}")
    print(f"  User Notification: {'✅ SUCCESS' if results['user_notification'] else '❌ FAILED'}")
    
    if results['errors']:
        print("\n❌ Errors:")
        for error in results['errors']:
            print(f"    - {error}")
    
    return results

def main():
    print("🔔 Quick Email Test")
    print("=" * 50)
    
    # Test configuration
    if not test_email_config():
        print("\n❌ Email configuration failed. Please check your .env file.")
        return
    
    # Send test notification
    results = send_test_notification()
    
    # Summary
    success_count = sum([results['technician_notification'], results['user_notification']])
    print(f"\n🎯 Summary: {success_count}/2 notifications sent")
    
    if success_count == 2:
        print("🎉 SUCCESS! Check your email at rohankul2017@gmail.com")
        print("You should receive 2 emails:")
        print("  1. 🎫 Technician Assignment Email")
        print("  2. ✅ User Confirmation Email")
    elif success_count == 1:
        print("⚠️ Partial success - only 1 email sent")
    else:
        print("❌ No emails sent - check configuration")

if __name__ == "__main__":
    main()
