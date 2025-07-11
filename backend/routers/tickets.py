from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models import Ticket, TicketCreate
from ..crud import (
    get_all_tickets, get_ticket_by_number, create_ticket, update_ticket_by_number, delete_ticket_by_number
)

router = APIRouter()

@router.get("/tickets/", response_model=List[Ticket])
def read_tickets():
    """Get all tickets"""
    tickets = get_all_tickets()
    return tickets

@router.get("/tickets/{ticket_number}", response_model=Ticket)
def read_ticket(ticket_number: str):
    ticket = get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/tickets/", response_model=Ticket)
def create_new_ticket(ticket: TicketCreate):
    """Create a new ticket"""
    created_ticket = create_ticket(ticket)
    if not created_ticket:
        raise HTTPException(status_code=400, detail="Failed to create ticket")
    return created_ticket

@router.put("/tickets/{ticket_number}", response_model=Ticket)
def update_ticket(ticket_number: str, status: Optional[str] = None, priority: Optional[str] = None):
    updated = update_ticket_by_number(ticket_number, status=status, priority=priority)
    if not updated:
        raise HTTPException(status_code=400, detail="No fields to update or update failed")
    ticket = get_ticket_by_number(ticket_number)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found after update")
    return ticket

@router.delete("/tickets/{ticket_number}")
def delete_ticket(ticket_number: str):
    deleted = delete_ticket_by_number(ticket_number)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found or could not be deleted")
    return {"detail": "Ticket deleted"} 