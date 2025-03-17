import streamlit as st
import sqlite3
import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import os
import random
import json
import base64
import re
from PIL import Image
import io
import plotly.express as px
from mock_flight_data import generate_mock_flights
from datetime import datetime, timedelta

# Database connection
def get_db_connection():
    """Get a database connection"""
    return sqlite3.connect("airline.db", check_same_thread=False)

# Function to create database tables
def create_tables():
    """Create database tables if they don't exist"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        is_admin INTEGER DEFAULT 0
    )
    ''')

    # Create flights table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS flights (
        id TEXT PRIMARY KEY,
        flight_number TEXT,
        airline TEXT,
        origin TEXT,
        destination TEXT,
        departure_date TEXT,
        departure_time TEXT,
        arrival_date TEXT,
        arrival_time TEXT,
        duration TEXT,
        aircraft TEXT,
        price REAL,
        seats_available INTEGER,
        class TEXT
    )
    ''')

    # Create reservations table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        flight_id TEXT,
        passenger_name TEXT,
        flight_number TEXT,
        seat_number TEXT,
        booking_date TEXT,
        status TEXT,
        ticket_id TEXT,
        extras TEXT DEFAULT 'None',
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    ''')

    # Check if there are any users in the database
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]

    # Insert sample user if none exist
    if user_count == 0:
        cursor.execute("INSERT INTO users (username, password, full_name, email, phone, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
                      ("admin", "admin123", "Admin User", "admin@example.com", "1234567890", 1))
        cursor.execute("INSERT INTO users (username, password, full_name, email, phone) VALUES (?, ?, ?, ?, ?)",
                      ("user", "user123", "Regular User", "user@example.com", "0987654321"))

    # Check if there are any airports in the database
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='airports'")
    airports_table_exists = cursor.fetchone()[0] > 0

    if not airports_table_exists:
        # Create airports table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS airports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            name TEXT,
            city TEXT,
            country TEXT
        )
        ''')

        # Insert sample airports
        sample_airports = [
            ("DEL", "Indira Gandhi International Airport", "New Delhi", "India"),
            ("BOM", "Chhatrapati Shivaji International Airport", "Mumbai", "India"),
            ("MAA", "Chennai International Airport", "Chennai", "India"),
            ("BLR", "Kempegowda International Airport", "Bengaluru", "India"),
            ("CCU", "Netaji Subhas Chandra Bose International Airport", "Kolkata", "India"),
            ("HYD", "Rajiv Gandhi International Airport", "Hyderabad", "India"),
            ("COK", "Cochin International Airport", "Kochi", "India"),
            ("JFK", "John F. Kennedy International Airport", "New York", "USA"),
            ("LHR", "Heathrow Airport", "London", "UK"),
            ("SIN", "Singapore Changi Airport", "Singapore", "Singapore")
        ]

        cursor.executemany("INSERT INTO airports (code, name, city, country) VALUES (?, ?, ?, ?)", sample_airports)

    conn.commit()
    conn.close()

# User Authentication
def authenticate(username, password):
    """Authenticate user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and user[1] == password:
            return True, "Login successful", user[0]
        return False, "Invalid username or password", None
    except Exception as e:
        return False, f"Error during authentication: {e}", None
    finally:
        conn.close()

def register(username, password, full_name, email, phone, address):
    try:
        cursor.execute("INSERT INTO users (username, password, full_name, email, phone, address) VALUES (?, ?, ?, ?, ?, ?)", (username, password, full_name, email, phone, address))
        conn.commit()
        return True
    except:
        return False

# User registration function
def register_user(username, password, full_name, email, phone, address=None):
    """Register a new user"""
    # Input validation
    if not username or not password:
        return False, "Username and password are required"
    
    # Check username length
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    # Check password strength
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists. Please choose another username."
        
        # Insert new user - include address parameter
        cursor.execute("""
            INSERT INTO users (username, password, full_name, email, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, full_name, email, phone, address or ""))
        
        conn.commit()
        
        # Get the new user's ID
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        user_id = cursor.fetchone()[0]
        
        return True, "Registration successful! Please log in.", user_id
    except Exception as e:
        return False, f"Error during registration: {e}", None
    finally:
        conn.close()

# Search Flights
def search_flights(origin, destination, departure_date=None, flight_class=None):
    """
    Search for flights between origin and destination airports
    Uses mock flight data generator to create realistic flight options
    
    Args:
        origin (str): Origin airport code
        destination (str): Destination airport code
        departure_date (str): Departure date in YYYY-MM-DD format
        flight_class (str): Flight class (Economy, Business, First)
        
    Returns:
        list: List of flight tuples with all necessary data
    """
    # Set default values for required parameters
    if flight_class is None:
        flight_class = "Economy"
    
    # Format the date if provided
    formatted_date = departure_date if departure_date else datetime.now().strftime("%Y-%m-%d")
    
    st.info(f"Searching for flights from {origin} to {destination} on {formatted_date}...")
    
    # Generate mock flight data
    flights = generate_mock_flights(origin, destination, formatted_date, flight_class)
    
    # Store the mock flights in the database for booking
    if flights:
        store_mock_flights(flights)
        return flights
    else:
        st.warning("No flights found for the selected criteria.")
        return []

def store_mock_flights(flights):
    """Store mock flights in the database so they can be booked"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start a transaction
        conn.execute("BEGIN TRANSACTION")
        
        for flight in flights:
            flight_id, flight_number, airline, origin, destination = flight[0:5]
            dep_date, dep_time, arr_date, arr_time, duration = flight[5:10]
            aircraft, price, seats, flight_class = flight[10:14]
            
            # Ensure all values have the correct data types
            flight_id = str(flight_id)  # Ensure flight_id is a string
            flight_number = str(flight_number)
            airline = str(airline)
            origin = str(origin)
            destination = str(destination)
            dep_date = str(dep_date)
            dep_time = str(dep_time)
            arr_date = str(arr_date)
            arr_time = str(arr_time)
            duration = str(duration)
            aircraft = str(aircraft)
            try:
                price = float(price)  # Ensure price is a float
            except (ValueError, TypeError):
                price = 0.0
            try:
                seats = int(seats)  # Ensure seats is an integer
            except (ValueError, TypeError):
                seats = 0
            flight_class = str(flight_class)
            
            # Check if this mock flight already exists in the database
            cursor.execute("SELECT id FROM flights WHERE flight_number = ?", (flight_number,))
            existing = cursor.fetchone()
            
            if not existing:
                # Insert the flight into the database
                cursor.execute('''
                    INSERT INTO flights (
                        id, flight_number, airline, origin, destination, 
                        departure_date, departure_time, arrival_date, arrival_time,
                        duration, aircraft, price, seats_available, class
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    flight_id,
                    flight_number, airline, origin, destination,
                    dep_date, dep_time, arr_date, arr_time,
                    duration, aircraft, price, seats, flight_class
                ))
        
        # Commit the transaction
        conn.commit()
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        print(f"Error storing mock flights: {e}")
    finally:
        conn.close()

def get_airport_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code, city, country FROM airports ORDER BY city")
    airports = cursor.fetchall()
    conn.close()
    return airports

def get_flight_details(flight_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.*, a1.city as origin_city, a1.country as origin_country, 
        a2.city as dest_city, a2.country as dest_country
        FROM flights f
        JOIN airports a1 ON f.origin = a1.code
        JOIN airports a2 ON f.destination = a2.code
        WHERE f.id = ?
    """, (flight_id,))
    flight = cursor.fetchone()
    conn.close()
    return flight

def get_flight_by_id(flight_id):
    """Get flight details by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
        flight = cursor.fetchone()
        return flight
    except Exception as e:
        print(f"Error getting flight details: {e}")
        return None
    finally:
        conn.close()

# Book Ticket
def book_ticket(passenger_name, flight_id, seat_number, user_id, extras="None"):
    """Book a ticket for a flight"""
    if not passenger_name or not flight_id or not seat_number or not user_id:
        return False, "All fields are required"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Convert user_id to integer to ensure correct data type
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return False, "Invalid user ID format"

        # Generate a ticket ID
        ticket_id = f"TKT-{random.randint(10000, 99999)}"
        
        # Get the actual flight number if we have a selected flight in session state
        flight_number = ""
        if 'selected_flight' in st.session_state and st.session_state.selected_flight is not None:
            flight = st.session_state.selected_flight
            if len(flight) > 1:  # Make sure flight data is available
                flight_number = f"{flight[2]} {flight[1]}"  # Airline + Flight Number
            else:
                flight_number = f"FLIGHT-{flight_id}"
        else:
            flight_number = f"FLIGHT-{flight_id}"
            
        # Get current date for booking
        booking_date = datetime.now().strftime("%Y-%m-%d")

        # First check if the reservations table has an extras column
        cursor.execute("PRAGMA table_info(reservations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "extras" not in columns:
            # Add the extras column if it doesn't exist
            cursor.execute("ALTER TABLE reservations ADD COLUMN extras TEXT DEFAULT 'None'")
            conn.commit()

        # Insert booking into reservations - use explicit type conversion
        cursor.execute("""
            INSERT INTO reservations 
            (user_id, flight_id, passenger_name, flight_number, seat_number, booking_date, status, ticket_id, extras)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,  # Integer
            str(flight_id),  # Ensure string
            str(passenger_name),  # Ensure string
            str(flight_number),  # Ensure string
            str(seat_number),  # Ensure string
            str(booking_date),  # Ensure string
            "Confirmed",  # String
            str(ticket_id),  # Ensure string
            str(extras)  # Ensure string
        ))
        
        conn.commit()
        return True, f"Ticket booked successfully! Your ticket ID is {ticket_id}"
    except Exception as e:
        return False, f"Error booking ticket: {e}"
    finally:
        conn.close()

# View Reservations
def view_reservations(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.id, r.passenger_name, r.flight_number, f.origin, f.destination, 
        f.departure_date, f.departure_time, r.seat_number, r.status, r.ticket_id, f.price
        FROM reservations r
        JOIN flights f ON r.flight_id = f.id
        WHERE r.user_id=?
        ORDER BY r.booking_date DESC
    """, (user_id,))
    reservations = cursor.fetchall()
    conn.close()
    return reservations

# Cancel Reservation
def cancel_reservation(reservation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT flight_id FROM reservations WHERE id=?", (reservation_id,))
    flight_id = cursor.fetchone()
    if flight_id:
        cursor.execute("UPDATE flights SET seats_available=seats_available+1 WHERE id=?", (flight_id[0],))
        cursor.execute("UPDATE reservations SET status='Cancelled' WHERE id=?", (reservation_id,))
        conn.commit()
        return True
    return False

# Cancel Booking
def cancel_booking(booking_id):
    """Cancel a booking by its ID and remove it from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First check if the booking exists
        cursor.execute("SELECT id FROM reservations WHERE id = ?", (booking_id,))
        if not cursor.fetchone():
            return False
        
        # Delete the booking
        cursor.execute("DELETE FROM reservations WHERE id = ?", (booking_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error cancelling booking: {e}")
        return False
    finally:
        conn.close()

# Generate E-Ticket PDF
def generate_ticket_pdf(booking):
    """Generate a printable ticket in PDF format"""
    try:
        # Extract booking details
        booking_id = booking[0]
        flight_id = booking[1]
        passenger_name = booking[2] 
        flight_number = booking[3]
        seat_number = booking[4]
        status = booking[5]
        ticket_id = booking[6]
        booking_date = booking[7] if len(booking) > 7 else datetime.now().strftime("%Y-%m-%d")
        
        # Create PDF
        pdf = canvas.Canvas(f"tickets/{ticket_id}.pdf", pagesize=letter)
        width, height = letter
        
        # Add airline logo/header
        pdf.setFont("Helvetica-Bold", 24)
        pdf.setFillColor(colors.black)
        pdf.drawString(100, height - 100, f"SkyWings Airlines")
        pdf.setFillColor(colors.black)
        
        # Add ticket header
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(100, height - 140, "BOARDING PASS")
        
        # Add horizontal line
        pdf.line(100, height - 150, width - 100, height - 150)
        
        # Passenger information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 180, "PASSENGER")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 200, passenger_name)
        
        # Flight information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 230, "FLIGHT")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 250, f"{flight_number} | {flight_id}")
        
        # Route information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 280, "FROM")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 300, f"{flight_id}")
        
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(300, height - 280, "TO")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(300, height - 300, f"{flight_id}")
        
        # Date and time information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 330, "DATE")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 350, booking_date)
        
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(300, height - 330, "TIME")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(300, height - 350, "10:00")
        
        # Seat and class information
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 380, "SEAT")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 400, seat_number)
        
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(300, height - 380, "CLASS")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(300, height - 400, "Economy")
        
        # Ticket ID and barcode (simulated)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(100, height - 430, "TICKET ID")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, height - 450, ticket_id)
        
        # Add horizontal line
        pdf.line(100, height - 480, width - 100, height - 480)
        
        # Footer
        pdf.setFont("Helvetica-Oblique", 10)
        pdf.drawString(100, height - 510, "This is an electronic ticket. Please present this document and a valid ID at check-in.")
        pdf.drawString(100, height - 530, f"Price: $100.00 | Issued on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        pdf.save()
        return f"tickets/{ticket_id}.pdf"
    except Exception as e:
        return f"<div>Error generating ticket: {e}</div>"

def get_user_bookings(user_id):
    """Get bookings for a user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if the reservations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reservations'")
        if not cursor.fetchone():
            # Table doesn't exist, return empty list
            return []
            
        # Check if the extras column exists
        cursor.execute("PRAGMA table_info(reservations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Build query based on available columns
        select_columns = "id, user_id, flight_id, passenger_name, flight_number, seat_number, booking_date, status, ticket_id"
        if "extras" in columns:
            select_columns += ", extras"
            
        cursor.execute(f"SELECT {select_columns} FROM reservations WHERE user_id = ?", (user_id,))
        bookings = cursor.fetchall()
        return bookings
    except Exception as e:
        print(f"Error fetching bookings: {e}")
        return []
    finally:
        conn.close()

def my_bookings_page():
    """Display user's bookings with ticket previews and management options"""
    st.markdown("""
    <div class="section-header">
        <h1>My Bookings</h1>
        <p>View and manage your flight reservations</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user bookings
    bookings = get_user_bookings(st.session_state.current_user_id)
    
    if bookings:
        for booking in bookings:
            try:
                # Get booking details
                booking_id = booking[0] if len(booking) > 0 else "N/A"
                user_id = booking[1] if len(booking) > 1 else "N/A"
                flight_id = booking[2] if len(booking) > 2 else "N/A"
                passenger_name = booking[3] if len(booking) > 3 else "N/A"
                flight_number = booking[4] if len(booking) > 4 else "N/A"
                seat_number = booking[5] if len(booking) > 5 else "N/A"
                booking_date = booking[6] if len(booking) > 6 else "N/A"
                status = booking[7] if len(booking) > 7 else "Confirmed"
                ticket_id = booking[8] if len(booking) > 8 else f"TKT-{random.randint(10000, 99999)}"
                extras = booking[9] if len(booking) > 9 else "None"
                
                # Get flight details for better display
                flight_details = get_flight_by_id(flight_id)
                
                # Set default values
                airline = "SkyWings"
                origin = "DEL"
                destination = "BOM"
                departure_date = booking_date
                departure_time = "10:00 AM"
                
                # If we have flight details, use them
                if flight_details and len(flight_details) >= 7:
                    flight_number = flight_details[1]
                    airline = flight_details[2]
                    origin = flight_details[3]
                    destination = flight_details[4]
                    departure_date = flight_details[5]
                    departure_time = flight_details[6]
                
                # Clean passenger name
                display_name = passenger_name
                if display_name and isinstance(display_name, str):
                    display_name = re.sub(r'(?i)\b\w*mock\w*\b', '', display_name).strip()
                    if not display_name:
                        display_name = "Passenger"
                
                # Clean flight number
                clean_flight_number = flight_number
                if isinstance(clean_flight_number, str):
                    clean_flight_number = re.sub(r'(?i)\b\w*mock\w*\b[\-]*', '', clean_flight_number).strip()
                    if not clean_flight_number:
                        clean_flight_number = f"SK{random.randint(100, 999)}"
                
                # Generate the ticket HTML
                ticket_html = generate_ticket_html(booking_id, display_name, airline, clean_flight_number, 
                                                origin, destination, departure_date, departure_time, 
                                                seat_number, extras, ticket_id)
                
                # Create an expander for each booking
                with st.expander(f"**{airline} {clean_flight_number}** | {departure_date} | {origin} to {destination}", expanded=True):
                    # Display ticket info in a card
                    st.markdown(f"""
                    <div class="card flight-card">
                        <h3>Flight Ticket: {ticket_id}</h3>
                        <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                            <div style="flex: 1; min-width: 200px;">
                                <p><strong>Airline:</strong> {airline}</p>
                                <p><strong>Flight:</strong> {clean_flight_number}</p>
                                <p><strong>From:</strong> {origin} <strong>To:</strong> {destination}</p>
                                <p><strong>Date:</strong> {departure_date} <strong>Time:</strong> {departure_time}</p>
                                <p><strong>Passenger:</strong> {display_name}</p>
                                <p><strong>Seat:</strong> {seat_number}</p>
                                <p><strong>Status:</strong> <span style="color: green; font-weight: bold;">{status}</span></p>
                                <p><strong>Additional Services:</strong> <span style="color: #000000;">{extras}</span></p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Download ticket button
                        if st.button("📄 Download Ticket", key=f"download_{booking_id}", use_container_width=True):
                            b64 = base64.b64encode(ticket_html.encode()).decode()
                            href = f'<a href="data:text/html;base64,{b64}" download="ticket_{booking_id}.html">Download Ticket</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            st.success("Ticket ready for download!")
                    
                    with col2:
                        # View ticket button
                        if st.button("👁️ View Ticket", key=f"view_{booking_id}", use_container_width=True):
                            st.components.v1.html(ticket_html, height=600)
                    
                    with col3:
                        # Cancel booking button with confirmation
                        cancel_state_key = f"cancel_state_{booking_id}"
                        
                        # Initialize the cancel state if not already in session
                        if cancel_state_key not in st.session_state:
                            st.session_state[cancel_state_key] = False
                        
                        # Show the cancel button if not in confirmation state
                        if not st.session_state[cancel_state_key]:
                            if st.button("❌ Cancel Booking", key=f"cancel_{booking_id}", use_container_width=True):
                                st.session_state[cancel_state_key] = True
                                st.rerun()
                        else:
                            # Show confirmation buttons
                            st.warning("Are you sure you want to cancel this booking? This cannot be undone.")
                            confirm_col1, confirm_col2 = st.columns(2)
                            
                            with confirm_col1:
                                if st.button("Yes, Cancel", key=f"confirm_cancel_{booking_id}", use_container_width=True):
                                    # Delete the booking
                                    if cancel_booking(booking_id):
                                        st.session_state[cancel_state_key] = False
                                        st.success("Booking successfully cancelled.")
                                        st.rerun()
                                    else:
                                        st.error("Failed to cancel booking. Please try again.")
                            
                            with confirm_col2:
                                if st.button("No, Keep", key=f"keep_{booking_id}", use_container_width=True):
                                    st.session_state[cancel_state_key] = False
                                    st.rerun()
            
            except Exception as e:
                st.error(f"Error displaying booking: {str(e)}")
                continue
    else:
        # No bookings found
        st.markdown("""
        <div class="card" style="text-align: center; padding: 2rem;">
            <h3>No Bookings Found</h3>
            <p>You haven't made any bookings yet.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Button to book a flight
        if st.button("Book a Flight Now", use_container_width=True):
            st.session_state.page = 'booking'
            st.rerun()

def generate_ticket_html(booking_id, passenger_name, airline, flight_number, 
                        origin, destination, departure_date, departure_time, 
                        seat, extras, ticket_id):
    """Generate HTML for a ticket"""
    
    # Format extras with commas if it's a list
    if isinstance(extras, list):
        extras = ", ".join(extras)
    
    # Current date for issue date
    issue_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create a clean, professional ticket
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flight Ticket - {ticket_id}</title>
        <style>
            body {{
                font-family: 'Arial', sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .ticket {{
                width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}
            .ticket-header {{
                background-color: #1e3a8a;
                color: white;
                padding: 20px;
                text-align: center;
            }}
            .ticket-header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .ticket-body {{
                padding: 20px;
                border-bottom: 1px dashed #ccc;
            }}
            .flight-info {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
            }}
            .flight-route {{
                text-align: center;
                margin: 20px 0;
            }}
            .airport {{
                font-size: 24px;
                font-weight: bold;
            }}
            .city {{
                font-size: 16px;
                color: #666;
            }}
            .arrow {{
                margin: 0 20px;
                font-size: 24px;
                color: #1e3a8a;
            }}
            .passenger-info {{
                margin-top: 20px;
                padding-top: 20px;
                border-top: 1px solid #eee;
            }}
            .info-row {{
                display: flex;
                margin-bottom: 10px;
            }}
            .info-label {{
                width: 150px;
                font-weight: bold;
                color: #666;
            }}
            .info-value {{
                flex: 1;
            }}
            .barcode {{
                text-align: center;
                margin-top: 20px;
                padding: 10px;
            }}
            .barcode img {{
                max-width: 300px;
            }}
            .ticket-footer {{
                padding: 20px;
                font-size: 12px;
                color: #999;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <div class="ticket-header">
                <h1>BOARDING PASS</h1>
                <p>{airline} - {flight_number}</p>
            </div>
            <div class="ticket-body">
                <div class="flight-info">
                    <div>
                        <div class="info-label">Passenger</div>
                        <div class="info-value" style="font-size: 18px; font-weight: bold;">{passenger_name}</div>
                    </div>
                    <div>
                        <div class="info-label">Ticket No.</div>
                        <div class="info-value">{ticket_id}</div>
                    </div>
                </div>
                
                <div class="flight-route">
                    <span class="airport">{origin}</span>
                    <span class="arrow">✈️</span>
                    <span class="airport">{destination}</span>
                </div>
                
                <div class="info-row">
                    <div class="info-label">Flight</div>
                    <div class="info-value">{airline} {flight_number}</div>
                </div>
                
                <div class="info-row">
                    <div class="info-label">Date</div>
                    <div class="info-value">{departure_date}</div>
                </div>
                
                <div class="info-row">
                    <div class="info-label">Departure</div>
                    <div class="info-value">{departure_time}</div>
                </div>
                
                <div class="info-row">
                    <div class="info-label">Seat</div>
                    <div class="info-value" style="font-size: 18px; font-weight: bold;">{seat}</div>
                </div>
                
                <div class="info-row">
                    <div class="info-label">Additional Services</div>
                    <div class="info-value">{extras if extras and extras != "None" else "No additional services"}</div>
                </div>
                
                <div class="passenger-info">
                    <div class="info-row">
                        <div class="info-label">Issue Date</div>
                        <div class="info-value">{issue_date}</div>
                    </div>
                </div>
                
                <div class="barcode">
                    <svg width="300" height="80">
                        <!-- Simple barcode representation -->
                        <rect x="10" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="20" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="35" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="45" y="10" width="15" height="60" fill="#000"></rect>
                        <rect x="65" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="75" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="90" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="100" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="115" y="10" width="15" height="60" fill="#000"></rect>
                        <rect x="135" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="145" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="160" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="170" y="10" width="15" height="60" fill="#000"></rect>
                        <rect x="190" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="200" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="215" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="225" y="10" width="15" height="60" fill="#000"></rect>
                        <rect x="245" y="10" width="5" height="60" fill="#000"></rect>
                        <rect x="255" y="10" width="10" height="60" fill="#000"></rect>
                        <rect x="270" y="10" width="15" height="60" fill="#000"></rect>
                    </svg>
                    <div>{ticket_id}</div>
                </div>
            </div>
            <div class="ticket-footer">
                <p>Please arrive at the airport at least 2 hours before your scheduled departure.</p>
                <p>This is an electronic ticket. Please present this along with a valid photo ID at check-in.</p>
                <p>&copy; {datetime.now().year} SkyWings Airlines. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def get_airport_codes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM airports")
    airport_codes = cursor.fetchall()
    conn.close()
    return [row[0] for row in airport_codes]

def get_user_details(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_name, email, phone, address FROM users WHERE id = ?", (user_id,))
    user_details = cursor.fetchone()
    conn.close()
    return user_details

def update_profile(user_id, full_name, email, phone, address):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET full_name = ?, email = ?, phone = ?, address = ?
        WHERE id = ?
    """, (full_name, email, phone, address, user_id))
    conn.commit()
    conn.close()

def login_page():
    """Display login form"""
    st.markdown("""
    <div class="section-header">
        <h1>SkyWings Airlines</h1>
        <p>Welcome to SkyWings Airlines Reservation System</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.image("https://img.freepik.com/free-vector/airplane-sky_1308-31202.jpg", width=500)
        
    
    with col2:
        st.markdown("<h2>Login</h2> ;", unsafe_allow_html=True)
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        login_col1, login_col2 = st.columns([1, 1])
        
        with login_col1:
            login_button = st.button("Login", use_container_width=True)
        
        with login_col2:
            register_button = st.button("Register", use_container_width=True)
        
        if login_button:
            success, message, user_id = authenticate(username, password)
            if success:
                st.session_state.logged_in = True
                st.session_state.current_user = username
                st.session_state.current_user_id = user_id
                st.session_state.page = 'booking'
                st.rerun()
            else:
                st.error(message)
                
        if register_button:
            st.session_state.page = 'register'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="card">
            <h3>Welcome to SkyWings Airlines</h3>
            <p>Experience the best in air travel with our premium services and comfortable flights.</p>
            <ul>
                <li>Best prices and deals</li>
                <li>24/7 customer support</li>
                <li>Convenient booking process</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        
def registration_page():
    """Display registration form"""
    st.markdown("""
    <div class="section-header">
        <h1>SkyWings Airlines - Registration</h1>
        <p>Create a new account to access our services</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.image("https://img.freepik.com/free-vector/airplane-sky_1308-31202.jpg", width=300)
        st.markdown("""
        <div class="card">
            <h3>Benefits of Registration</h3>
            <p>Join SkyWings Airlines and enjoy these benefits:</p>
            <ul>
                <li>Quick and easy booking process</li>
                <li>Access to exclusive deals and promotions</li>
                <li>View and manage your bookings</li>
                <li>Personalized travel experience</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h2>Create Account</h2>", unsafe_allow_html=True)
        
        username = st.text_input("Username*")
        password = st.text_input("Password*", type="password")
        confirm_password = st.text_input("Confirm Password*", type="password")
        full_name = st.text_input("Full Name*")
        email = st.text_input("Email*")
        phone = st.text_input("Phone Number")
        address = st.text_input("Address")
        
        register_col1, register_col2 = st.columns([1, 1])
        
        with register_col1:
            register_button = st.button("Create Account", use_container_width=True, key="create_account")
        
        with register_col2:
            back_button = st.button("Back to Login", use_container_width=True)
        
        if register_button:
            if not username or not password or not confirm_password or not full_name or not email:
                st.error("Please fill in all required fields.")
            elif password != confirm_password:
                st.error("Passwords do not match. Please try again.")
            else:
                success, message, user_id = register_user(username, password, full_name, email, phone, address)
                if success:
                    st.success("Registration successful! Please login with your new credentials.")
                    st.session_state.page = 'login'
                    st.rerun()
                else:
                    st.error(message)
                    
        if back_button:
            st.session_state.page = 'login'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def booking_page():
    """Display flight booking page"""
    st.markdown("""
    <div class="section-header">
        <h1>Book Your Flight</h1>
        <p>Search and book flights to your desired destinations</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Flight Search Form
    col1, col2 = st.columns(2)
    
    with col1:
        # Get airports from the database
        origin = st.selectbox("Origin", get_airport_codes())
        origin_code = origin
        
        departure_date = st.date_input("Departure Date", min_value=datetime.now().date())
    
    with col2:
        destination = st.selectbox("Destination", get_airport_codes())
        destination_code = destination
        
        flight_class = st.selectbox("Class", ["Economy", "Business", "First"])
    
    if st.button("Search Flights", use_container_width=True):
        if origin == destination:
            st.error("Origin and destination cannot be the same.")
        else:
            formatted_date = departure_date.strftime("%Y-%m-%d")
            flights = search_flights(origin_code, destination_code, formatted_date, flight_class)
            st.session_state.flights = flights
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Display Flight Results
    if 'flights' in st.session_state and st.session_state.flights:
        st.markdown("""
        <div class="section-header" style="background-color: #004d99; margin-top: 2rem;">
            <h3>Available Flights</h3>
            <p>Select a flight to proceed with booking</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_count = 2
        flight_chunks = [st.session_state.flights[i:i + col_count] for i in range(0, len(st.session_state.flights), col_count)]
        
        for chunk in flight_chunks:
            cols = st.columns(col_count)
            for i, flight in enumerate(chunk):
                if i < len(cols):
                    with cols[i]:
                        st.markdown(f"""
                        <div class="flight-card">
                            <h4>{flight[2]} {flight[1]}</h4>
                            <p><strong>From:</strong> {flight[3]} <strong>To:</strong> {flight[4]}</p>
                            <p><strong>Date:</strong> {flight[5]} <strong>Time:</strong> {flight[6]}</p>
                            <p><strong>Duration:</strong> {flight[7]}</p>
                            <p><strong>Price:</strong> ${flight[8]}</p>
                            <p><strong>Class:</strong> {flight[9]}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button(f"Select Flight", key=f"flight_{flight[0]}", use_container_width=True):
                            st.session_state.selected_flight = flight
                            st.session_state.page = 'flight_booking_form'
                            st.rerun()
    
    # Show message if no flights found
    elif 'flights' in st.session_state and not st.session_state.flights:
        st.warning("No flights found matching your criteria. Please try different search parameters.")

def flight_booking_form_page():
    if 'selected_flight' not in st.session_state or st.session_state.selected_flight is None:
        st.warning("No flight selected. Please search and select a flight first.")
        st.session_state.page = 'booking'
        st.rerun()
    
    flight = st.session_state.selected_flight
    
    # Page header
    st.markdown(f"""
    <div class="section-header">
        <h1>Complete Your Booking</h1>
        <p>Enter passenger details and preferences</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Flight details card
    st.markdown(f"""
    <div class="detail-section">
        <h4>Selected Flight: {flight[2]} {flight[1]}</h4>
        <p><strong>From:</strong> {flight[3]} to <strong>To:</strong> {flight[4]}</p>
        <p><strong>Date:</strong> {flight[5]} <strong>Time:</strong> {flight[6]}</p>
        <p><strong>Duration:</strong> {flight[7]}</p>
        <p><strong>Price:</strong> ${flight[8]}</p>
        <p><strong>Class:</strong> {flight[9]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Booking form
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        passenger_name = st.text_input("Passenger Full Name", placeholder="Enter passenger's full name as in ID")
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            passenger_email = st.text_input("Email", placeholder="example@email.com")
        with col1_2:
            passenger_phone = st.text_input("Phone Number", placeholder="+1 234 567 8900")
        
    with col2:
        st.markdown("<h4>Select Seat</h4>", unsafe_allow_html=True)
        
        # Create a visual seat map
        seat_cols = st.columns(6)
        seat_options = [f"{row}{num}" for row in "ABCDEF" for num in range(1, 6)]
        selected_seat = st.selectbox("Choose your seat", seat_options)
        
        st.markdown("<h4>Additional Services</h4>", unsafe_allow_html=True)
        
        service_col1, service_col2 = st.columns(2)
        with service_col1:
            st.markdown('<div style="color: #000000;">', unsafe_allow_html=True)
            extra_baggage = st.checkbox("Extra Baggage (+$30)")
            priority_boarding = st.checkbox("Priority Boarding (+$15)")
            st.markdown('</div>', unsafe_allow_html=True)
        with service_col2:
            meal_preference = st.selectbox("Meal Preference", ["Standard Meal", "Vegetarian", "Vegan", "Gluten-Free", "No Meal"])
            seat_preference = st.selectbox("Seat Preference", ["No Preference", "Window", "Aisle", "Extra Legroom"])
        
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            book_button = st.button("Confirm Booking", use_container_width=True, key="confirm_booking_btn")
        with submit_col2:
            cancel_button = st.button("Cancel", use_container_width=True, key="cancel_booking_btn")
    
    if book_button:
        if not passenger_name or not selected_seat:
            st.error("Passenger name and seat number are required")
        else:
            # Calculate extras
            extras = []
            extra_cost = 0
            if extra_baggage:
                extras.append("Extra Baggage")
                extra_cost += 30
            if priority_boarding:
                extras.append("Priority Boarding")
                extra_cost += 15
            
            # Book the flight
            success, message = book_ticket(
                passenger_name=passenger_name, 
                flight_id=flight[0], 
                seat_number=selected_seat, 
                user_id=st.session_state.current_user_id,
                extras=", ".join(extras) if extras else "None"
            )
            
            if success:
                st.success(message)
                # Reset selected flight
                st.session_state.selected_flight = None
                # Navigate to My Bookings
                st.session_state.page = 'my_bookings'
                st.rerun()
            else:
                st.error(message)
    
    if cancel_button:
        st.session_state.selected_flight = None
        st.session_state.page = 'booking'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def profile_page():
    """Display user profile page"""
    st.markdown("""
    <div class="section-header">
        <h1>My Profile</h1>
        <p>View and update your personal information</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user details
    user_details = get_user_details(st.session_state.current_user_id)
    
    if user_details:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<h3>Personal Information</h3>", unsafe_allow_html=True)
            full_name = st.text_input("Full Name", value=user_details[0] if len(user_details) > 0 else "")
            email = st.text_input("Email", value=user_details[1] if len(user_details) > 1 else "")
            phone = st.text_input("Phone", value=user_details[2] if len(user_details) > 2 else "")
        
        with col2:
            st.markdown("<h3>Account Details</h3>", unsafe_allow_html=True)
            # Display username (this is the current user from session state)
            username = st.text_input("Username", value=st.session_state.current_user, disabled=True)
            # Address is the 4th element (index 3)
            address = st.text_area("Address", value=user_details[3] if len(user_details) > 3 else "")
            new_password = st.text_input("New Password (leave blank to keep current)", type="password")
        
        if st.button("Update Profile", use_container_width=True):
            update_profile(
                st.session_state.current_user_id,
                full_name,
                email,
                phone,
                address
            )
            st.success("Profile updated successfully!")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Show booking statistics
        bookings = get_user_bookings(st.session_state.current_user_id)
        
        st.markdown("""
        <div class="detail-section" style="margin-top: 2rem;">
            <h3>Account Statistics</h3>
        </div>
        """, unsafe_allow_html=True)
        
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.markdown(f"""
            <div class="card" style="text-align: center;">
                <h1>{len(bookings)}</h1>
                <p>Total Bookings</p>
            </div>
            """, unsafe_allow_html=True)
        
        with stat_col2:
            # Calculate upcoming flights - handle both date formats (with and without time)
            upcoming_flights = 0
            for booking in bookings:
                if booking and len(booking) > 6 and booking[6]:
                    try:
                        # Try to parse with full datetime format first
                        if ' ' in booking[6]:
                            booking_date = datetime.strptime(booking[6].split()[0], "%Y-%m-%d").date()
                        else:
                            booking_date = datetime.strptime(booking[6], "%Y-%m-%d").date()
                        
                        if booking_date >= datetime.now().date():
                            upcoming_flights += 1
                    except ValueError:
                        # Skip this booking if we can't parse the date
                        pass
            
            st.markdown(f"""
            <div class="card" style="text-align: center;">
                <h1>{upcoming_flights}</h1>
                <p>Upcoming Flights</p>
            </div>
            """, unsafe_allow_html=True)
        
        with stat_col3:
            # Random miles as a fun stat
            import random
            miles = random.randint(1000, 10000)
            
            st.markdown(f"""
            <div class="card" style="text-align: center;">
                <h1>{miles}</h1>
                <p>SkyWings Miles</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("Could not retrieve user details. Please try again later.")
        
# Streamlit UI
def main():
    st.set_page_config(
        page_title="SkyWings Airline Reservation System",
        page_icon="✈️",
        layout="wide"
    )
    
    # Create tables if they don't exist
    create_tables()
    
    # Add custom CSS for styling
    st.markdown("""
    <style>
    /* Set all headings to black by default */
    h1, h2, h3, h4, h5, h6 {
        color: #000000;
    }
    p {
        color: Black;
    }
    
    .main {
        background-color: #f8fafc;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .css-18e3th9 {
        padding-top: 2rem;
    }
    .css-1d391kg {
        padding: 1rem;
    }
    .block-container {
        max-width: 1100px;
        padding: 2rem;
    }
    .stButton>button {
        background-color: #1e40af;
        color: white;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .stButton>button:hover {
        background-color: #1e3a8a;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .card {
        background-color: white;
        color: #111827;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .card:hover {
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .section-header {
        background-color: #1e3a8a;
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    /* Override section-header headings to ensure contrast on dark background */
    .section-header h1, .section-header h2, .section-header h3 {
        color: white;
        margin-bottom: 0.5rem;
    }
    .section-header p {
        color: #e5e7eb;
        margin-bottom: 0;
        font-size: 1.1rem;
    }
    .flight-card {
        background-color: white;
        color: #111827;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .flight-card:hover {
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
    }
    .flight-card h4 {
        color: #000000;
        margin-bottom: 0.5rem;
    }
    .flight-card p {
        color: #000000;
        margin-bottom: 0.5rem;
    }
    .flight-card strong {
        color: #374151;
    }
    .select-flight-btn {
        background-color: #1e40af;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        cursor: pointer;
        width: 100%;
        transition: all 0.3s ease;
    }
    .select-flight-btn:hover {
        background-color: #1e3a8a;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        border-radius: 4px;
        border: 1px solid #d1d5db;
    }
    .stTextInput>label, .stSelectbox>label, .stDateInput>label {
        color: #374151;
        font-weight: 500;
    }
    .detail-section {
        background-color: white;
        color: #111827;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-left: 5px solid #1e3a8a;
    }
    .detail-section h4 {
        color: #000000;
        margin-bottom: 0.5rem;
    }
    .detail-section p {
        margin-bottom: 0.5rem;
    }
    .detail-section strong {
        color: #374151;
    }
    .sidebar .css-1k0ckh2 {
        background-color: #f8fafc;
    }
    a {
        color: #1e40af;
        text-decoration: none;
    }
    a:hover {
        color: #1e3a8a;
        text-decoration: underline;
    }
    .css-1yjuwjr, .css-qrbaxs {
        font-size: 16px;
        color: #374151;
    }
    
    /* Style Streamlit checkboxes text to be black */
    .stCheckbox > label {
        color: #000000 !important;
        font-weight: normal;
    }
    
    /* Style Streamlit error, success, and info messages */
    .st-emotion-cache-16idsys, .st-emotion-cache-1gulp4b, .st-emotion-cache-1altryn {
        color: #000000 !important;
    }
    
    /* Error message style */
    .st-emotion-cache-183lzff {
        background-color: #ffe6e6;
        border-left-color: #ff4d4d;
    }
    .st-emotion-cache-183lzff p {
        color: #000000 !important;
    }
    
    /* Success message style */
    .st-emotion-cache-1erivf3 {
        background-color: #e6ffe6;
        border-left-color: #33cc33;
    }
    .st-emotion-cache-1erivf3 p {
        color: #000000 !important;
    }
    
    /* Info message style */
    .st-emotion-cache-16wtyzk {
        background-color: #e6f2ff;
        border-left-color: #3399ff;
    }
    .st-emotion-cache-16wtyzk p {
        color: #000000 !important;
    }
    
    /* Warning message style */
    .st-emotion-cache-7ym5gk {
        background-color: #fff9e6;
        border-left-color: #ffcc00;
    }
    .st-emotion-cache-7ym5gk p {
        color: #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state variables if they don't exist
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'current_user_id' not in st.session_state:
        st.session_state.current_user_id = None
    if 'page' not in st.session_state:
        st.session_state.page = 'login'
    if 'flights' not in st.session_state:
        st.session_state.flights = []
    if 'selected_flight' not in st.session_state:
        st.session_state.selected_flight = None
    
    # Page navigation based on session state
    if not st.session_state.logged_in:
        if st.session_state.page == 'login':
            login_page()
        elif st.session_state.page == 'register':
            registration_page()
        else:
            st.session_state.page = 'login'
            login_page()
    else:
        # Sidebar for navigation
        with st.sidebar:
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; margin-bottom: 2rem; background-color: #1e3a8a; color: white; border-radius: 10px;">
                <h2 style="color: white;">Welcome, {st.session_state.current_user}!</h2>
                <p>SkyWings Airlines</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<h3 style='text-align: center; color: #000000;'>Navigation</h3>", unsafe_allow_html=True)
            
            if st.button("✈️ Book Flight", use_container_width=True):
                st.session_state.page = 'booking'
                st.session_state.selected_flight = None
                st.rerun()
                
            if st.button("🎫 My Bookings", use_container_width=True):
                st.session_state.page = 'my_bookings'
                st.rerun()
                
            if st.button("👤 My Profile", use_container_width=True):
                st.session_state.page = 'profile'
                st.rerun()
                
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.current_user = None
                st.session_state.current_user_id = None
                st.session_state.page = 'login'
                st.session_state.selected_flight = None
                st.rerun()
        
        # Main content based on page
        if st.session_state.page == 'booking':
            booking_page()
        elif st.session_state.page == 'flight_booking_form':
            flight_booking_form_page()
        elif st.session_state.page == 'my_bookings':
            my_bookings_page()
        elif st.session_state.page == 'profile':
            profile_page()
        else:
            booking_page()  # Default to booking page

def flight_booking_form_page():
    """Display dedicated form for completing flight booking"""
    if 'selected_flight' not in st.session_state or st.session_state.selected_flight is None:
        st.warning("No flight selected. Please search and select a flight first.")
        st.session_state.page = 'booking'
        st.rerun()
    
    flight = st.session_state.selected_flight
    
    # Page header
    st.markdown(f"""
    <div class="section-header">
        <h1>Complete Your Booking</h1>
        <p>Enter passenger details and preferences</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Flight details card
    st.markdown(f"""
    <div class="detail-section">
        <h4>Selected Flight: {flight[2]} {flight[1]}</h4>
        <p><strong>From:</strong> {flight[3]} to <strong>To:</strong> {flight[4]}</p>
        <p><strong>Date:</strong> {flight[5]} <strong>Time:</strong> {flight[6]}</p>
        <p><strong>Duration:</strong> {flight[7]}</p>
        <p><strong>Price:</strong> ${flight[8]}</p>
        <p><strong>Class:</strong> {flight[9]}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Booking form
    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        passenger_name = st.text_input("Passenger Full Name", placeholder="Enter passenger's full name as in ID")
        
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            passenger_email = st.text_input("Email", placeholder="example@email.com")
        with col1_2:
            passenger_phone = st.text_input("Phone Number", placeholder="+1 234 567 8900")
        
    with col2:
        st.markdown("<h4>Select Seat</h4>", unsafe_allow_html=True)
        
        # Create a visual seat map
        seat_cols = st.columns(6)
        seat_options = [f"{row}{num}" for row in "ABCDEF" for num in range(1, 6)]
        selected_seat = st.selectbox("Choose your seat", seat_options)
        
        st.markdown("<h4>Additional Services</h4>", unsafe_allow_html=True)
        
        service_col1, service_col2 = st.columns(2)
        with service_col1:
            st.markdown('<div style="color: #000000;">', unsafe_allow_html=True)
            extra_baggage = st.checkbox("Extra Baggage (+$30)")
            priority_boarding = st.checkbox("Priority Boarding (+$15)")
            st.markdown('</div>', unsafe_allow_html=True)
        with service_col2:
            meal_preference = st.selectbox("Meal Preference", ["Standard Meal", "Vegetarian", "Vegan", "Gluten-Free", "No Meal"])
            seat_preference = st.selectbox("Seat Preference", ["No Preference", "Window", "Aisle", "Extra Legroom"])
        
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            book_button = st.button("Confirm Booking", use_container_width=True, key="confirm_booking_btn")
        with submit_col2:
            cancel_button = st.button("Cancel", use_container_width=True, key="cancel_booking_btn")
    
    if book_button:
        if not passenger_name or not selected_seat:
            st.error("Passenger name and seat number are required")
        else:
            # Calculate extras
            extras = []
            extra_cost = 0
            if extra_baggage:
                extras.append("Extra Baggage")
                extra_cost += 30
            if priority_boarding:
                extras.append("Priority Boarding")
                extra_cost += 15
            
            # Book the flight
            success, message = book_ticket(
                passenger_name=passenger_name, 
                flight_id=flight[0], 
                seat_number=selected_seat, 
                user_id=st.session_state.current_user_id,
                extras=", ".join(extras) if extras else "None"
            )
            
            if success:
                st.success(message)
                # Reset selected flight
                st.session_state.selected_flight = None
                # Navigate to My Bookings
                st.session_state.page = 'my_bookings'
                st.rerun()
            else:
                st.error(message)
    
    if cancel_button:
        st.session_state.selected_flight = None
        st.session_state.page = 'booking'
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Run the main function
if __name__ == "__main__":
    main()
