import random
from datetime import datetime, timedelta

def generate_mock_flights(origin, destination, departure_date, flight_class="Economy"):
    """
    Generate mock flight data for the airline reservation system
    
    Args:
        origin (str): Origin airport code
        destination (str): Destination airport code
        departure_date (str): Departure date in YYYY-MM-DD format
        flight_class (str): Flight class (Economy, Business, First)
        
    Returns:
        list: List of flight tuples with all necessary data
    """
    # Common airlines
    airlines = [
        {"code": "AI", "name": "Air India"},
        {"code": "BA", "name": "British Airways"},
        {"code": "LH", "name": "Lufthansa"},
        {"code": "EK", "name": "Emirates"},
        {"code": "QR", "name": "Qatar Airways"},
        {"code": "SQ", "name": "Singapore Airlines"}
    ]
    
    # Aircraft types
    aircraft_types = [
        "Boeing 777-300ER",
        "Boeing 787-9",
        "Airbus A380-800",
        "Airbus A350-900",
        "Boeing 737-800",
        "Airbus A320neo"
    ]
    
    # Convert departure_date to datetime
    try:
        dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
    except:
        # If date parsing fails, use current date
        dep_date = datetime.now()
    
    # Generate 5-6 flights
    num_flights = random.randint(5, 6)
    flights = []
    
    # Morning, afternoon, and evening departure times
    departure_hours = [7, 9, 12, 14, 17, 20]
    
    for i in range(num_flights):
        # Select airline
        airline = airlines[i % len(airlines)]
        airline_code = airline["code"]
        airline_name = airline["name"]
        
        # Generate flight number
        flight_number = f"{airline_code}{random.randint(100, 999)}"
        
        # Generate departure time
        dep_hour = departure_hours[i % len(departure_hours)]
        dep_minute = random.choice([0, 15, 30, 45])
        departure_time = f"{dep_hour:02d}:{dep_minute:02d}"
        
        # Generate arrival time (1-3 hours after departure)
        duration = random.randint(60, 180)  # Duration in minutes
        arr_hour = dep_hour + (dep_minute + duration) // 60
        arr_minute = (dep_minute + duration) % 60
        if arr_hour >= 24:
            arr_hour = arr_hour % 24
        arrival_time = f"{arr_hour:02d}:{arr_minute:02d}"
        
        # Calculate arrival date
        dep_datetime = dep_date.replace(hour=dep_hour, minute=dep_minute, second=0, microsecond=0)
        arr_datetime = dep_datetime + timedelta(minutes=duration)
        arrival_date = arr_datetime.strftime("%Y-%m-%d")
        
        # Generate aircraft type
        aircraft = aircraft_types[i % len(aircraft_types)]
        
        # Generate price based on flight class
        base_price = random.randint(2000, 5000)  # Base price between 2000-5000
        if flight_class == "Business":
            price = base_price * 2.5
        elif flight_class == "First":
            price = base_price * 4.0
        else:  # Economy
            price = base_price
        
        # Ensure price is a clean integer
        price = int(round(price))
        
        # Generate available seats
        available_seats = random.randint(5, 50)
        
        # Create flight data tuple
        flight_data = (
            i + 1,  # flight id
            flight_number,
            airline_name,
            origin,
            destination,
            dep_date.strftime("%Y-%m-%d"),
            departure_time,
            arrival_time,
            price,  # price is now an integer
            available_seats,
            flight_class
        )
        flights.append(flight_data)
    
    # Sort flights by departure time
    flights.sort(key=lambda x: x[6])
    
    return flights
