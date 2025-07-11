from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models import Technician, TechnicianCreate, TechnicianUpdate
from ..crud import (
    get_all_technicians, get_technician_by_id, create_technician,
    update_technician_by_id, delete_technician_by_id
)

router = APIRouter()

@router.get("/technicians/", response_model=List[Technician])
def read_all_technicians():
    """Get all technicians"""
    technicians = get_all_technicians()
    return technicians

@router.get("/technicians/{technician_id}", response_model=Technician)
def read_technician(technician_id: str):
    """Get a specific technician by ID"""
    tech = get_technician_by_id(technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech

@router.post("/technicians/", response_model=Technician)
def create_new_technician(technician: TechnicianCreate):
    """Create a new technician"""
    # Check if technician already exists
    existing_tech = get_technician_by_id(technician.technician_id)
    if existing_tech:
        raise HTTPException(status_code=400, detail="Technician with this ID already exists")

    created_tech = create_technician(technician)
    if not created_tech:
        raise HTTPException(status_code=500, detail="Failed to create technician")
    return created_tech

@router.put("/technicians/{technician_id}", response_model=Technician)
def update_technician(technician_id: str, technician_update: TechnicianUpdate):
    """Update a technician by ID"""
    # Check if technician exists
    existing_tech = get_technician_by_id(technician_id)
    if not existing_tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    updated = update_technician_by_id(technician_id, technician_update)
    if not updated:
        raise HTTPException(status_code=400, detail="No fields to update or update failed")

    tech = get_technician_by_id(technician_id)
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found after update")
    return tech

@router.delete("/technicians/{technician_id}")
def delete_technician(technician_id: str):
    """Delete a technician by ID"""
    # Check if technician exists
    existing_tech = get_technician_by_id(technician_id)
    if not existing_tech:
        raise HTTPException(status_code=404, detail="Technician not found")

    deleted = delete_technician_by_id(technician_id)
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete technician")
    return {"detail": "Technician deleted successfully"}