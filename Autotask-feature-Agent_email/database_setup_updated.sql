-- Updated Database Setup for Assignment Agent
-- MAX_WORKLOAD and AVAILABILITY_STATUS columns have been removed
-- Availability is now checked dynamically via Google Calendar API

-- Create the technician table with updated schema
CREATE TABLE IF NOT EXISTS TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA (
    TECHNICIAN_ID VARCHAR(50),
    NAME VARCHAR(100),
    EMAIL VARCHAR(100),
    ROLE VARCHAR(100),
    SKILLS VARCHAR(1000),  -- JSON array or comma-separated
    CURRENT_WORKLOAD INTEGER,
    SPECIALIZATIONS VARCHAR(1000)  -- JSON array or comma-separated
);

-- Clear existing data (optional)
-- DELETE FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA;

-- Insert sample technician data (without max_workload and availability_status)
-- Availability is now checked dynamically via Google Calendar API
INSERT INTO TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA VALUES
('TECH-001', 'John Smith', 'john.smith@company.com', 'Email Specialist',
 '["Exchange Server", "Email Configuration", "Outlook Support", "SMTP", "IMAP"]',
 2, '["Email", "Microsoft Exchange", "Office 365"]'),

('TECH-002', 'Jane Doe', 'jane.doe@company.com', 'Hardware Technician',
 '["Hardware Troubleshooting", "PC Repair", "Printer Support", "Desktop Support"]',
 1, '["Hardware", "Desktop Support", "Peripherals"]'),

('TECH-003', 'Mike Johnson', 'mike.johnson@company.com', 'Network Administrator',
 '["Network Troubleshooting", "Router Configuration", "WiFi Setup", "Firewall", "VPN"]',
 3, '["Network", "Infrastructure", "Security"]'),

('TECH-004', 'Sarah Wilson', 'sarah.wilson@company.com', 'Software Specialist',
 '["Software Installation", "Application Support", "Troubleshooting", "Windows", "macOS"]',
 0, '["Software", "Applications", "Operating Systems"]'),

('TECH-005', 'David Brown', 'david.brown@company.com', 'Security Analyst',
 '["Security Analysis", "Antivirus Support", "Access Control", "Incident Response"]',
 1, '["Security", "Compliance", "Risk Management"]'),

('TECH-006', 'Lisa Garcia', 'lisa.garcia@company.com', 'Database Administrator',
 '["SQL Database", "Database Administration", "Data Recovery", "MySQL", "PostgreSQL"]',
 2, '["Database", "Data Management", "SQL"]'),

('TECH-007', 'Tom Anderson', 'tom.anderson@company.com', 'Server Administrator',
 '["Windows Server", "Linux Server", "Server Administration", "Active Directory"]',
 1, '["Server", "Infrastructure", "System Administration"]'),

('TECH-008', 'Emily Chen', 'emily.chen@company.com', 'IT Support Specialist',
 '["General IT Support", "Help Desk", "User Training", "Basic Troubleshooting"]',
 0, '["General Support", "Help Desk", "User Assistance"]');

-- Verify the data
SELECT
    TECHNICIAN_ID,
    NAME,
    EMAIL,
    ROLE,
    CURRENT_WORKLOAD,
    SKILLS,
    SPECIALIZATIONS
FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
ORDER BY CURRENT_WORKLOAD ASC, NAME ASC;

-- Example queries for testing

-- Get all technicians (availability checked via Google Calendar)
SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
ORDER BY CURRENT_WORKLOAD ASC;

-- Get technicians by role
SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA 
WHERE ROLE LIKE '%Email%';

-- Get technicians with specific skills
SELECT * FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA 
WHERE SKILLS LIKE '%Exchange Server%';

-- Count total technicians (availability checked dynamically via Google Calendar)
SELECT COUNT(*) as TOTAL_TECHNICIANS
FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA;

-- Show current workload distribution
SELECT 
    CURRENT_WORKLOAD,
    COUNT(*) as TECHNICIAN_COUNT,
    STRING_AGG(NAME, ', ') as TECHNICIANS
FROM TEST_DB.PUBLIC.TECHNICIAN_DUMMY_DATA
GROUP BY CURRENT_WORKLOAD
ORDER BY CURRENT_WORKLOAD;
