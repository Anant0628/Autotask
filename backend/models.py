from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class Ticket(BaseModel):
    ticket_number: str = Field(..., alias="TICKETNUMBER")
    issue_type: str
    sub_issue_type: str
    ticket_category: str
    priority: str
    description: str
    # requester_name: Optional[str] = None  # Commented out for now - removed from response
    # requester_email: Optional[EmailStr] = None  # Commented out for now - removed from response
    due_date: str  # ISO format string
    status: Optional[str] = None
    CREATEDATE: str = Field(alias="CREATEDATE")
    # updated_at: Optional[datetime] = None  # Commented out completely

class TicketCreate(BaseModel):
    """Model for creating a new ticket"""
    ticket_number: str = Field(..., description="Unique ticket identifier")
    issue_type: str = Field(..., description="Type of issue")
    sub_issue_type: str = Field(..., description="Sub-type of issue")
    ticket_category: str = Field(..., description="Ticket category")
    priority: str = Field(..., description="Priority level")
    description: str = Field(..., description="Ticket description")
    status: str = Field(..., description="Ticket status")
    due_date: str = Field(..., description="Due date")
    CREATEDATE: str = Field(..., description="Creation date")

class Technician(BaseModel):
    technician_id: str = Field(..., alias="TECHNICIAN_ID")
    name: str = Field(..., alias="NAME")
    email: str = Field(..., alias="EMAIL")  # Changed from EmailStr to str to match DB
    role: str = Field(..., alias="ROLE")
    skills: str = Field(..., alias="SKILLS")  # Changed to str to match DB VARCHAR(500)
    availability_status: Optional[str] = Field(None, alias="AVAILABILITY_STATUS")
    current_workload: Optional[str] = Field(None, alias="CURRENT_WORKLOAD")  # Changed to str to match DB
    specializations: Optional[str] = Field(None, alias="SPECIALIZATIONS")  # Changed to str to match DB

class TechnicianCreate(BaseModel):
    """Model for creating a new technician - all fields required as per database schema"""
    technician_id: str = Field(..., description="Unique technician identifier")
    name: str = Field(..., max_length=50, description="Technician name")
    email: str = Field(..., max_length=100, description="Technician email")
    role: str = Field(..., max_length=50, description="Technician role")
    skills: str = Field(..., max_length=500, description="Technician skills")
    availability_status: str = Field(..., description="Current availability status")
    current_workload: str = Field(..., description="Current workload")
    specializations: str = Field(..., description="Technician specializations")

class TechnicianUpdate(BaseModel):
    """Model for updating technician fields"""
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[str] = None
    availability_status: Optional[str] = None
    current_workload: Optional[str] = None
    specializations: Optional[str] = None