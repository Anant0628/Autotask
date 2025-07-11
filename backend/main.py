from fastapi import FastAPI
from .routers import tickets, technicians
from .database import connect_snowflake, close_snowflake

app = FastAPI()

@app.on_event("startup")
def startup_event():
    connect_snowflake()

@app.on_event("shutdown")
def shutdown_event():
    close_snowflake()

app.include_router(tickets.router)
app.include_router(technicians.router)

@app.get("/")
def read_root():
    return {"message": "FastAPI backend is running!"} 