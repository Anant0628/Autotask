# 📧 Gmail Email Integration Setup Guide

## 🚀 Quick Start

The email integration has been successfully implemented using your Gmail logic. Here's how to set it up and use it:

## 📋 Prerequisites

1. **Install dateparser** (recommended for advanced date parsing):
   ```bash
   pip install dateparser
   ```

2. **Gmail App Password**: You'll need a Gmail App Password for secure authentication.

## 🔧 Setup Steps

### 1. Create Gmail App Password

1. Go to your Google Account settings
2. Navigate to Security → 2-Step Verification
3. At the bottom, select "App passwords"
4. Generate a new app password for "Mail"
5. Copy the 16-character password

### 2. Set Environment Variable

Create a `.env` file in your project root or set the environment variable:

```bash
# In .env file
SUPPORT_EMAIL_PASSWORD=your_16_character_app_password_here
```

Or set it in your system:
```bash
# Windows
set SUPPORT_EMAIL_PASSWORD=your_16_character_app_password_here

# Linux/Mac
export SUPPORT_EMAIL_PASSWORD=your_16_character_app_password_here
```

### 3. Update Email Configuration

The system is configured to use:
- **Email**: `rohankul2017@gmail.com` (as per your code)
- **Server**: `imap.gmail.com`
- **Folder**: `inbox`
- **Timezone**: `Asia/Kolkata`
- **Lookback**: 180 minutes (3 hours)

## 🎯 Usage Options

### Option 1: Standalone Script (Recommended for Testing)

Run the standalone Gmail processing script:

```bash
python process_gmail_tickets.py
```

This script will:
- ✅ Connect to Gmail
- ✅ Find all **unseen** emails
- ✅ Process them through the intake agent
- ✅ Create tickets with AI classification
- ✅ Mark emails as **seen** after processing

### Option 2: Integrated with Streamlit UI

Run the main application:

```bash
streamlit run app_refactored.py
```

Features:
- ✅ **Email Service Controls** in the sidebar
- ✅ **Start/Stop** background email processing
- ✅ **Check Now** button for manual processing
- ✅ **Email Notifications** when tickets are created
- ✅ **Email Statistics** and recent email tickets display

## 📊 How It Works

### Email Processing Flow:
```
📧 Unseen Gmail → 🔍 Extract Data → 🤖 AI Processing → 🎫 Create Ticket → ✅ Mark as Seen
```

### Data Extracted from Each Email:
- **Name**: Sender's name (or email username if name not available)
- **Email**: Sender's email address
- **Title**: Email subject
- **Description**: Email body content
- **Due Date**: Extracted using NLP patterns:
  - "tomorrow" → next day
  - "next Friday" → next Friday
  - "in 3 working days" → 3 business days
  - Advanced parsing with dateparser
  - Fallback: 48 hours from received time

### AI Processing:
- **Metadata Extraction**: Categories, types, priorities
- **Similar Ticket Search**: Find related historical tickets
- **Classification**: Automatic categorization and priority assignment
- **Resolution Notes**: AI-generated resolution suggestions

## 🎨 UI Features

### Sidebar Controls:
- **📧 Email Service Status**: Shows if service is running
- **▶️ Start/⏹️ Stop**: Control background processing
- **🔄 Check Now**: Manual email check
- **📊 Statistics**: Total tickets and email tickets count

### Notifications:
- **Success Popups**: "📧 Ticket successfully raised via email: [Title]"
- **Dismissible Alerts**: Click ✕ to dismiss notifications
- **Ticket Details**: Expandable details for each email ticket

### Dashboard:
- **📧 Recent Email Tickets**: Dedicated section for email-generated tickets
- **🎯 Recent Activity**: Combined view of all tickets

## 🔧 Configuration Options

### Email Processor Settings:
```python
# In email_processor.py or process_gmail_tickets.py
EMAIL_ACCOUNT = 'rohankul2017@gmail.com'
MINUTES_BACK = 180  # How far back to look (3 hours)
MAX_EMAILS = 50     # Maximum emails to process per run
DEFAULT_DUE_OFFSET_HOURS = 48  # Default due date offset
```

### Background Service:
```python
# Check interval for background processing
check_interval_minutes = 5  # Check every 5 minutes
```

## 🧪 Testing

### Test with Mock Data:
```bash
python test_email_integration.py
```

### Test with Real Emails:
1. Send a test email to `rohankul2017@gmail.com`
2. Run: `python process_gmail_tickets.py`
3. Check the output for ticket creation
4. Verify in the Streamlit UI

## 🚨 Important Notes

### Security:
- ✅ **Never commit passwords** to version control
- ✅ **Use environment variables** for sensitive data
- ✅ **Use Gmail App Passwords**, not your regular password

### Email Processing:
- ✅ **Only unseen emails** are processed
- ✅ **Emails are marked as seen** after processing
- ✅ **Time-based filtering** prevents processing old emails
- ✅ **Error handling** for malformed emails

### Performance:
- ✅ **Configurable limits** prevent overwhelming the system
- ✅ **Background processing** doesn't block the UI
- ✅ **Efficient IMAP operations** with proper connection management

## 🎉 Success Indicators

When everything is working correctly, you should see:

1. **Console Output**:
   ```
   🚀 Starting Gmail Email Processing...
   [*] Connecting to Gmail server...
   [*] Found 2 unseen emails
   ✅ Processed ticket for email from John Doe: Network Issue
   [*] Marked email as seen
   🎉 Email processing complete!
   ```

2. **UI Notifications**:
   - Green success alerts: "📧 Ticket successfully raised via email: Network Issue"
   - Updated statistics in sidebar
   - New entries in Recent Email Tickets section

3. **Database**:
   - New entries in `Knowledgebase.json`
   - Tickets marked with `email_source` metadata

## 🔍 Troubleshooting

### Common Issues:

1. **"No module named 'dateparser'"**:
   ```bash
   pip install dateparser
   ```

2. **"Authentication failed"**:
   - Check Gmail App Password
   - Verify environment variable is set
   - Ensure 2FA is enabled on Gmail

3. **"No unseen emails found"**:
   - Check if emails are already marked as read
   - Verify email account and folder settings
   - Check time window (MINUTES_BACK)

4. **Snowflake connection errors**:
   - Verify Snowflake credentials in config
   - Check network connectivity
   - Ensure proper permissions

## 📞 Support

If you encounter issues:
1. Check the console output for detailed error messages
2. Verify all environment variables are set correctly
3. Test with the standalone script first
4. Check Gmail settings and app password

The integration is now **complete and ready to use**! 🎉
