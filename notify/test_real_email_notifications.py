"""
Test script to send real email notifications using the Notify Agent.
This will send actual emails to rohankul2017@gmail.com for testing.
"""

from notify_agent import NotifyAgent
from datetime import datetime


def test_real_email_sending():
    """Test sending real emails to rohankul2017@gmail.com"""
    
    print("📧 Testing Real Email Notifications")
    print("=" * 50)
    
    # Initialize Notify Agent (will use environment variables for email config)
    notify_agent = NotifyAgent()
    
    # Create test ticket data
    test_ticket = {
        'ticket_id': f'TEST-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
        'issue': 'Network connectivity test issue',
        'description': 'This is a test notification from the Notify Agent system. The user reported that they cannot access the shared network drive and are getting a "Network path not found" error message. This started happening after the latest Windows update this morning.',
        'due_date': '2024-01-15',
        'priority': 'High',
        'category': 'Network',
        'technician_name': 'John Smith',
        'technician_email': 'rohankul2017@gmail.com',  # Your email for technician notification
        'user_name': 'Test User',
        'user_email': 'rohankul2017@gmail.com'  # Your email for user notification
    }
    
    print("📋 Test Ticket Details:")
    print(f"  Ticket ID: {test_ticket['ticket_id']}")
    print(f"  Issue: {test_ticket['issue']}")
    print(f"  Priority: {test_ticket['priority']}")
    print(f"  Category: {test_ticket['category']}")
    print(f"  Technician: {test_ticket['technician_name']} ({test_ticket['technician_email']})")
    print(f"  User: {test_ticket['user_name']} ({test_ticket['user_email']})")
    
    print("\n🚀 Sending notifications...")
    
    # Send notifications
    results = notify_agent.process_ticket_assignment(test_ticket)
    
    # Display results
    print("\n📊 Results:")
    print(f"  Ticket ID: {results['ticket_id']}")
    print(f"  Timestamp: {results['timestamp']}")
    print(f"  Technician Notification: {'✅ SUCCESS' if results['technician_notification'] else '❌ FAILED'}")
    print(f"  User Notification: {'✅ SUCCESS' if results['user_notification'] else '❌ FAILED'}")
    
    if results['errors']:
        print("\n❌ Errors:")
        for error in results['errors']:
            print(f"    - {error}")
    
    # Summary
    success_count = sum([results['technician_notification'], results['user_notification']])
    print(f"\n🎯 Summary: {success_count}/2 notifications sent successfully")
    
    if success_count == 2:
        print("🎉 All notifications sent! Check your email inbox at rohankul2017@gmail.com")
        print("\n📧 You should receive 2 emails:")
        print("  1. 🎫 Technician Assignment Email - with ticket details")
        print("  2. ✅ User Confirmation Email - assignment confirmation")
    elif success_count == 1:
        print("⚠️ Partial success - only 1 notification sent")
    else:
        print("❌ No notifications sent - check email configuration")
    
    return results


def test_multiple_categories():
    """Test notifications for different ticket categories"""
    
    print("\n📧 Testing Multiple Categories")
    print("=" * 50)
    
    notify_agent = NotifyAgent()
    
    categories = ['Network', 'Hardware', 'Software', 'Security']
    results = []
    
    for i, category in enumerate(categories, 1):
        print(f"\n🎫 Test {i}/4: {category} Category")
        print("-" * 30)
        
        test_ticket = {
            'ticket_id': f'{category.upper()}-{datetime.now().strftime("%H%M%S")}',
            'issue': f'{category} test issue',
            'description': f'This is a test {category.lower()} issue for notification testing.',
            'due_date': '2024-01-15',
            'priority': 'Medium',
            'category': category,
            'technician_name': f'{category} Specialist',
            'technician_email': 'rohankul2017@gmail.com',
            'user_name': 'Test User',
            'user_email': 'rohankul2017@gmail.com'
        }
        
        result = notify_agent.process_ticket_assignment(test_ticket)
        results.append(result)
        
        success = result['technician_notification'] and result['user_notification']
        print(f"  Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    # Summary
    total_success = sum(1 for r in results if r['technician_notification'] and r['user_notification'])
    print(f"\n📊 Category Test Summary: {total_success}/{len(categories)} categories successful")
    
    return results


def main():
    """Main test function"""
    
    print("🔔 Real Email Notification Testing")
    print("=" * 60)
    print("⚠️  WARNING: This will send real emails to rohankul2017@gmail.com")
    print("=" * 60)
    
    # Test 1: Single notification
    print("\n🧪 Test 1: Single Notification")
    test1_results = test_real_email_sending()
    
    # Test 2: Multiple categories (optional)
    print("\n🧪 Test 2: Multiple Categories")
    user_input = input("\nDo you want to test multiple categories? (y/n): ").lower().strip()
    
    if user_input == 'y':
        test2_results = test_multiple_categories()
    else:
        print("⏭️ Skipping multiple category test")
        test2_results = []
    
    # Final summary
    print("\n🎯 Final Test Summary")
    print("=" * 60)
    
    if test1_results['technician_notification'] and test1_results['user_notification']:
        print("✅ Basic notification test: PASSED")
    else:
        print("❌ Basic notification test: FAILED")
    
    if test2_results:
        successful_categories = sum(1 for r in test2_results if r['technician_notification'] and r['user_notification'])
        print(f"✅ Category tests: {successful_categories}/{len(test2_results)} passed")
    
    print("\n💡 What to check in your email:")
    print("📧 Technician emails should have:")
    print("  - Subject: 🎫 New Ticket Assignment - [TICKET_ID]")
    print("  - Ticket details, due date, priority, description")
    print("  - Professional HTML formatting")
    
    print("\n📧 User emails should have:")
    print("  - Subject: ✅ Ticket Assignment Confirmation - [TICKET_ID]")
    print("  - Assignment confirmation message")
    print("  - Technician name and expected resolution date")
    
    print("\n🎉 Email notification testing complete!")
    print("Check your inbox at rohankul2017@gmail.com for the test emails.")


if __name__ == "__main__":
    main()
