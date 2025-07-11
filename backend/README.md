# FastAPI Backend for AutoTask

## Setup & Run

1. **Install dependencies**

```bash
pip install fastapi uvicorn snowflake-connector-python python-dotenv
```

2. **Set up your .env file**

Make sure you have a `.env` file in the backend root or project root with your Snowflake credentials:

```
SF_USER=your_user
SF_PASSWORD=your_password
SF_ACCOUNT=your_account
SF_WAREHOUSE=your_warehouse
SF_DATABASE=your_database
SF_SCHEMA=your_schema
SF_ROLE=your_role
SF_PASSCODE=your_passcode
```

3. **Run the FastAPI server**

```bash
uvicorn backend.main:app --reload --app-dir ..
```

The API will be available at: http://127.0.0.1:8000

## API Documentation

Visit http://127.0.0.1:8000/docs for interactive Swagger UI.

---

## Manual Endpoint Testing (Examples)

### Tickets (Bash)

- **Get all tickets:**
  ```bash
  curl http://127.0.0.1:8000/tickets/
  ```
- **Get ticket by number:**
  ```bash
  curl http://127.0.0.1:8000/tickets/T20240916.0053
  ```
- **Update ticket (status/priority):**
  ```bash
  curl -X PUT "http://127.0.0.1:8000/tickets/T20240916.0053?status=Resolved&priority=High"
  ```
- **Delete ticket:**
  ```bash
  curl -X DELETE http://127.0.0.1:8000/tickets/TKT-001
  ```

### Technicians (Bash)

- **Get technician by ID:**
  ```bash
  curl http://127.0.0.1:8000/technicians/T101
  ```
- **Update technician:**
  ```bash
  curl -X PUT "http://127.0.0.1:8000/technicians/TECH-001?name=John%20Doe&role=Lead%20Technician"
  ```
- **Delete technician:**
  ```bash
  curl -X DELETE http://127.0.0.1:8000/technicians/TECH-001
  ```

---

For more, use the Swagger UI at `/docs` or Redoc at `/redoc`. 

### Technicians (Windows PowerShell)

-**Get all technicians:**
'''
 powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/technicians/' | ConvertTo-Json -Depth 10"
'''
- **Get technician by ID:**
'''
 powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/technicians/T101' | ConvertTo-Json -Depth 10"
''' 

- **Create new technician:**
'''
echo '{"technician_id": "T115", "name": "Test User", "email": "test.user@example.com", "role": "IT Support", "skills": "Basic troubleshooting, Hardware setup", "availability_status": "Available", "current_workload": "0", "specializations": "General Support"}' > new_technician.json
'''
'''
  powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/technicians/' -Method POST -ContentType 'application/json' -InFile 'new_technician.json' | ConvertTo-Json -Depth 10"
'''   
- **tickets**
'''
   powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/tickets/T20250111.0001' | ConvertTo-Json -Depth 10"
'''

'''
  powershell -Command "Invoke-RestMethod -Uri 'http://127.0.0.1:8000/tickets/?limit=5' | ConvertTo-Json -Depth 10"
'''  