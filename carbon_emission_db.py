import sqlite3
import os


def setup_database():
    # Delete the database file if it exists
    if os.path.exists('carbon_emission.db'):
        os.remove('carbon_emission.db')
    
    conn = sqlite3.connect('carbon_emission.db')
    cursor = conn.cursor()
    
    # Create tables based on the schema
    cursor.execute('''
    CREATE TABLE User_Profile (
        User_ID INTEGER PRIMARY KEY,
        Full_Name VARCHAR(100),
        Email VARCHAR(100),
        Location VARCHAR(100)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Transportation (
        Transport_ID INTEGER PRIMARY KEY,
        User_ID INTEGER,
        Vehicle_Type VARCHAR(50),
        Distance_KM FLOAT,
        Date DATE,
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Energy_Consumption (
        Energy_ID INTEGER PRIMARY KEY,
        User_ID INTEGER,
        Energy_Source VARCHAR(50),
        Consumption_KWH FLOAT,
        Date DATE,
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Waste_Management (
        Waste_ID INTEGER PRIMARY KEY,
        User_ID INTEGER,
        Waste_Type VARCHAR(50),
        Waste_Weight_KG FLOAT,
        Date DATE,
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Industrial_Activity (
        Industry_ID INTEGER PRIMARY KEY,
        User_ID INTEGER,
        Activity_Type VARCHAR(100),
        Emission_Produced FLOAT,
        Date DATE,
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Emission_Factor (
        Factor_ID INTEGER PRIMARY KEY,
        Source_Type VARCHAR(50),
        Emission_Per_Unit FLOAT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Emission_Record (
        Record_ID INTEGER PRIMARY KEY,
        Factor_ID INTEGER,
        Source_Type VARCHAR(50),
        Source_ID INTEGER,
        Emission_Amount FLOAT,
        Date DATE,
        FOREIGN KEY (Factor_ID) REFERENCES Emission_Factor(Factor_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Sustainability_Program (
        Program_ID INTEGER PRIMARY KEY,
        Program_Name VARCHAR(100),
        Description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE User_Program (
        User_ID INTEGER,
        Program_ID INTEGER,
        Enrollment_Date DATE,
        PRIMARY KEY (User_ID, Program_ID),
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID),
        FOREIGN KEY (Program_ID) REFERENCES Sustainability_Program(Program_ID)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE Carbon_Offset (
        Offset_ID INTEGER PRIMARY KEY,
        User_ID INTEGER,
        Offset_Type VARCHAR(50),
        Offset_Amount FLOAT,
        Date DATE,
        FOREIGN KEY (User_ID) REFERENCES User_Profile(User_ID)
    )
    ''')
    
    # Insert demo data
    # User_Profile
    users = [
        (1, 'John Doe', 'john.doe@email.com', 'New York'),
        (2, 'Jane Smith', 'jane.smith@email.com', 'Los Angeles'),
        (3, 'Robert Johnson', 'robert.j@email.com', 'Chicago'),
        (4, 'Emily Davis', 'emily.d@email.com', 'Houston'),
        (5, 'Michael Wilson', 'michael.w@email.com', 'Phoenix')
    ]
    cursor.executemany('INSERT INTO User_Profile VALUES (?, ?, ?, ?)', users)
    
    # Transportation
    transportations = [
        (1, 1, 'Car', 150.5, '2023-01-15'),
        (2, 1, 'Bus', 75.2, '2023-02-10'),
        (3, 2, 'Train', 200.0, '2023-01-22'),
        (4, 3, 'Electric Car', 120.3, '2023-02-05'),
        (5, 4, 'Bicycle', 30.0, '2023-01-30'),
        (6, 5, 'Car', 180.7, '2023-02-15'),
        (7, 2, 'Airplane', 2500.0, '2023-03-01'),
        (8, 3, 'Bus', 90.5, '2023-03-10')
    ]
    cursor.executemany('INSERT INTO Transportation VALUES (?, ?, ?, ?, ?)', transportations)
    
    # Energy_Consumption
    energy_consumptions = [
        (1, 1, 'Electricity', 350.0, '2023-01-31'),
        (2, 2, 'Natural Gas', 200.5, '2023-01-31'),
        (3, 3, 'Electricity', 400.2, '2023-01-31'),
        (4, 4, 'Solar', 150.0, '2023-01-31'),
        (5, 5, 'Electricity', 320.7, '2023-01-31'),
        (6, 1, 'Natural Gas', 180.3, '2023-02-28'),
        (7, 2, 'Electricity', 370.5, '2023-02-28'),
        (8, 3, 'Wind', 100.0, '2023-02-28')
    ]
    cursor.executemany('INSERT INTO Energy_Consumption VALUES (?, ?, ?, ?, ?)', energy_consumptions)
    
    # Waste_Management
    waste_managements = [
        (1, 1, 'Plastic', 5.2, '2023-01-20'),
        (2, 2, 'Paper', 3.7, '2023-01-25'),
        (3, 3, 'Organic', 8.0, '2023-01-15'),
        (4, 4, 'Glass', 4.5, '2023-01-10'),
        (5, 5, 'Metal', 2.3, '2023-01-05'),
        (6, 1, 'Electronic', 1.5, '2023-02-15'),
        (7, 2, 'Plastic', 6.0, '2023-02-20'),
        (8, 3, 'Paper', 4.2, '2023-02-25')
    ]
    cursor.executemany('INSERT INTO Waste_Management VALUES (?, ?, ?, ?, ?)', waste_managements)
    
    # Industrial_Activity
    industrial_activities = [
        (1, 1, 'Manufacturing', 500.0, '2023-01-15'),
        (2, 2, 'Construction', 750.5, '2023-01-20'),
        (3, 3, 'Chemical Processing', 820.0, '2023-01-25'),
        (4, 4, 'Food Processing', 350.2, '2023-01-30'),
        (5, 5, 'Textile Production', 420.7, '2023-02-05'),
        (6, 1, 'Manufacturing', 510.3, '2023-02-10'),
        (7, 2, 'Construction', 730.0, '2023-02-15'),
        (8, 3, 'Chemical Processing', 800.5, '2023-02-20')
    ]
    cursor.executemany('INSERT INTO Industrial_Activity VALUES (?, ?, ?, ?, ?)', industrial_activities)
    
    # Emission_Factor
    # NOTE:
    # Transport factors were previously off by ~10x (values like 2.31 kg/km
    # instead of 0.231 kg/km). These have been corrected below so that, for
    # example, an 18.18 km car trip is in the ~4 kg CO2e range instead of ~42 kg.
    # For waste, we now store factors per waste type (Plastic, Paper, etc.)
    # instead of a single generic 'Waste' factor.
    emission_factors = [
        # Transportation (kg CO2e per km)
        (1, 'Car', 0.231),
        (2, 'Bus', 0.089),
        (3, 'Train', 0.041),
        (4, 'Airplane', 0.875),
        # Energy (kg CO2e per kWh)
        (5, 'Electricity', 0.45),
        (6, 'Natural Gas', 0.20),
        (7, 'Coal', 0.34),
        # Industrial – illustrative factors (kept simple)
        (8, 'Manufacturing', 5.20),
        (9, 'Construction', 4.35),
        # Waste (kg CO2e per kg), per material type
        # Values are approximate and mainly intended to keep
        # the relative ordering realistic (plastic > paper > glass, etc.).
        (10, 'Plastic', 3.0),      # 10 kg ≈ 30 kg CO2e
        (11, 'Paper', 1.5),
        (12, 'Glass', 0.5),
        (13, 'Metal', 2.0),
        (14, 'Organic', 1.0),
        (15, 'Electronic', 4.0),
        (16, 'Hazardous', 3.5),
    ]
    cursor.executemany('INSERT INTO Emission_Factor VALUES (?, ?, ?)', emission_factors)
    
    # Emission_Record
    emission_records = [
        (1, 1, 'Car', 1, 347.65, '2023-01-15'),
        (2, 2, 'Bus', 2, 66.92, '2023-02-10'),
        (3, 3, 'Train', 3, 82.00, '2023-01-22'),
        (4, 5, 'Electricity', 1, 157.50, '2023-01-31'),
        (5, 6, 'Natural Gas', 2, 40.10, '2023-01-31'),
        (6, 8, 'Manufacturing', 1, 2600.00, '2023-01-15'),
        (7, 9, 'Construction', 2, 3264.67, '2023-01-20'),
        (8, 10, 'Waste', 1, 3.02, '2023-01-20')
    ]
    cursor.executemany('INSERT INTO Emission_Record VALUES (?, ?, ?, ?, ?, ?)', emission_records)
    
    # Sustainability_Program
    sustainability_programs = [
        (1, 'Green Energy Initiative', 'Promoting renewable energy sources'),
        (2, 'Zero Waste Challenge', 'Reducing waste through recycling and composting'),
        (3, 'Carbon Footprint Reduction', 'Activities to reduce personal carbon footprint'),
        (4, 'Sustainable Transportation', 'Promoting eco-friendly transportation methods'),
        (5, 'Energy Efficiency Program', 'Improving energy efficiency at home and work')
    ]
    cursor.executemany('INSERT INTO Sustainability_Program VALUES (?, ?, ?)', sustainability_programs)
    
    # User_Program
    user_programs = [
        (1, 1, '2022-12-01'),
        (1, 3, '2023-01-05'),
        (2, 2, '2022-11-15'),
        (3, 4, '2022-12-20'),
        (4, 5, '2023-01-10'),
        (5, 1, '2022-11-01'),
        (2, 3, '2023-02-05'),
        (3, 2, '2023-01-15')
    ]
    cursor.executemany('INSERT INTO User_Program VALUES (?, ?, ?)', user_programs)
    
    # Carbon_Offset
    carbon_offsets = [
        (1, 1, 'Tree Planting', 50.0, '2023-01-10'),
        (2, 2, 'Renewable Energy Credits', 100.0, '2023-01-15'),
        (3, 3, 'Methane Capture', 75.5, '2023-01-20'),
        (4, 4, 'Tree Planting', 30.0, '2023-01-25'),
        (5, 5, 'Renewable Energy Credits', 120.0, '2023-01-30'),
        (6, 1, 'Methane Capture', 85.0, '2023-02-05'),
        (7, 2, 'Tree Planting', 45.0, '2023-02-10'),
        (8, 3, 'Renewable Energy Credits', 110.0, '2023-02-15')
    ]
    cursor.executemany('INSERT INTO Carbon_Offset VALUES (?, ?, ?, ?, ?)', carbon_offsets)
    
    conn.commit()
    conn.close()
    
    print("Database created successfully with demo data!")


def ensure_correct_emission_factors(db_path: str = "carbon_emission.db") -> None:
    """
    Ensure the Emission_Factor table contains the updated, realistic factors.
    This is safe to run on existing databases and will not touch user activity data.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Make sure the table exists (older/corrupt DBs)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Emission_Factor (
            Factor_ID INTEGER PRIMARY KEY,
            Source_Type VARCHAR(50),
            Emission_Per_Unit FLOAT
        )
        """
    )

    # Desired factors (same values as in setup_database, but managed by Source_Type)
    desired = {
        "Car": 0.231,
        "Bus": 0.089,
        "Train": 0.041,
        "Airplane": 0.875,
        "Electricity": 0.45,
        "Natural Gas": 0.20,
        "Coal": 0.34,
        "Manufacturing": 5.20,
        "Construction": 4.35,
        # Waste (per type, kg CO2e per kg)
        "Plastic": 3.0,
        "Paper": 1.5,
        "Glass": 0.5,
        "Metal": 2.0,
        "Organic": 1.0,
        "Electronic": 4.0,
        "Hazardous": 3.5,
    }

    for source, factor in desired.items():
        cursor.execute(
            "UPDATE Emission_Factor SET Emission_Per_Unit = ? WHERE Source_Type = ?",
            (factor, source),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO Emission_Factor (Source_Type, Emission_Per_Unit) VALUES (?, ?)",
                (source, factor),
            )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    setup_database()