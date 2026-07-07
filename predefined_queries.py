predefined_queries = {
    "Show All Users": "SELECT * FROM User_Profile",
    
    "Show All Transportation Records": "SELECT * FROM Transportation",
    
    "Show All Energy Consumption Records": "SELECT * FROM Energy_Consumption",
    
    "Show All Waste Management Records": "SELECT * FROM Waste_Management",
    
    "Show All Industrial Activities": "SELECT * FROM Industrial_Activity",
    
    "Show All Emission Factors": "SELECT * FROM Emission_Factor",
    
    "Show All Emission Records": "SELECT * FROM Emission_Record",
    
    "Show All Sustainability Programs": "SELECT * FROM Sustainability_Program",
    
    "Show All User Programs": "SELECT * FROM User_Program",
    
    "Show All Carbon Offsets": "SELECT * FROM Carbon_Offset",
    
    "Total Emissions By User": """
    SELECT up.User_ID, up.Full_Name, SUM(er.Emission_Amount) as Total_Emissions
    FROM User_Profile up
    LEFT JOIN Emission_Record er ON er.Source_ID = up.User_ID
    GROUP BY up.User_ID
    ORDER BY Total_Emissions DESC
    """,
    
    "Monthly Energy Consumption": """
    SELECT strftime('%Y-%m', ec.Date) as Month, SUM(ec.Consumption_KWH) as Total_KWH
    FROM Energy_Consumption ec
    GROUP BY Month
    ORDER BY Month
    """,
    
    "Users with Highest Carbon Footprint": """
    SELECT up.User_ID, up.Full_Name, SUM(er.Emission_Amount) as Carbon_Footprint
    FROM User_Profile up
    JOIN Emission_Record er ON er.Source_ID = up.User_ID
    GROUP BY up.User_ID
    ORDER BY Carbon_Footprint DESC
    LIMIT 5
    """,
    
    "Most Common Transportation Type": """
    SELECT Vehicle_Type, COUNT(*) as Count
    FROM Transportation
    GROUP BY Vehicle_Type
    ORDER BY Count DESC
    """,
    
    "Total Waste by Type": """
    SELECT Waste_Type, SUM(Waste_Weight_KG) as Total_Weight
    FROM Waste_Management
    GROUP BY Waste_Type
    ORDER BY Total_Weight DESC
    """,
    
    "Users in Green Energy Initiative": """
    SELECT up.User_ID, up.Full_Name, sp.Program_Name, usp.Enrollment_Date
    FROM User_Profile up
    JOIN User_Program usp ON up.User_ID = usp.User_ID
    JOIN Sustainability_Program sp ON usp.Program_ID = sp.Program_ID
    WHERE sp.Program_Name = 'Green Energy Initiative'
    """,
    
    "Average Emission by Industry Type": """
    SELECT Activity_Type, AVG(Emission_Produced) as Average_Emission
    FROM Industrial_Activity
    GROUP BY Activity_Type
    ORDER BY Average_Emission DESC
    """,
    
    "Carbon Offset Contribution": """
    SELECT up.User_ID, up.Full_Name, SUM(co.Offset_Amount) as Total_Offset
    FROM User_Profile up
    JOIN Carbon_Offset co ON up.User_ID = co.User_ID
    GROUP BY up.User_ID
    ORDER BY Total_Offset DESC
    """,
    
    "Transportation vs Energy Consumption": """
    SELECT up.User_ID, up.Full_Name, 
           SUM(CASE WHEN er.Source_Type IN ('Car', 'Bus', 'Train', 'Airplane') THEN er.Emission_Amount ELSE 0 END) as Transport_Emission,
           SUM(CASE WHEN er.Source_Type IN ('Electricity', 'Natural Gas', 'Coal') THEN er.Emission_Amount ELSE 0 END) as Energy_Emission
    FROM User_Profile up
    LEFT JOIN Emission_Record er ON er.Source_ID = up.User_ID
    GROUP BY up.User_ID
    """,
    
    "Emission Reduction Over Time": """
    SELECT strftime('%Y-%m', er.Date) as Month, SUM(er.Emission_Amount) as Total_Emission
    FROM Emission_Record er
    GROUP BY Month
    ORDER BY Month
    """,
    
    "Top Carbon Offset Methods": """
    SELECT Offset_Type, SUM(Offset_Amount) as Total_Offset
    FROM Carbon_Offset
    GROUP BY Offset_Type
    ORDER BY Total_Offset DESC
    """,
    
    "Users With Most Sustainability Programs": """
    SELECT up.User_ID, up.Full_Name, COUNT(usp.Program_ID) as Program_Count
    FROM User_Profile up
    JOIN User_Program usp ON up.User_ID = usp.User_ID
    GROUP BY up.User_ID
    ORDER BY Program_Count DESC
    """,
    
    "Compare Car vs Public Transport Usage": """
    SELECT up.User_ID, up.Full_Name,
           SUM(CASE WHEN t.Vehicle_Type = 'Car' THEN t.Distance_KM ELSE 0 END) as Car_Distance,
           SUM(CASE WHEN t.Vehicle_Type IN ('Bus', 'Train') THEN t.Distance_KM ELSE 0 END) as Public_Transport_Distance
    FROM User_Profile up
    LEFT JOIN Transportation t ON up.User_ID = t.User_ID
    GROUP BY up.User_ID
    """,
    
    "Most Eco-Friendly User": """
    SELECT up.User_ID, up.Full_Name, 
           COUNT(DISTINCT usp.Program_ID) as Program_Count,
           SUM(co.Offset_Amount) as Total_Offset,
           SUM(er.Emission_Amount) as Total_Emission
    FROM User_Profile up
    LEFT JOIN User_Program usp ON up.User_ID = usp.User_ID
    LEFT JOIN Carbon_Offset co ON up.User_ID = co.User_ID
    LEFT JOIN Emission_Record er ON er.Source_ID = up.User_ID
    GROUP BY up.User_ID
    ORDER BY (Program_Count + Total_Offset - Total_Emission) DESC
    LIMIT 1
    """,
    
    "Program Effectiveness": """
    SELECT sp.Program_ID, sp.Program_Name,
           AVG(er1.Emission_Amount - er2.Emission_Amount) as Average_Reduction
    FROM User_Program usp
    JOIN Sustainability_Program sp ON usp.Program_ID = sp.Program_ID
    JOIN Emission_Record er1 ON er1.Source_ID = usp.User_ID AND er1.Date < usp.Enrollment_Date
    JOIN Emission_Record er2 ON er2.Source_ID = usp.User_ID AND er2.Date > usp.Enrollment_Date
    GROUP BY sp.Program_ID
    ORDER BY Average_Reduction DESC
    """,
    
    "Waste Reduction by Month": """
    SELECT strftime('%Y-%m', wm.Date) as Month, SUM(wm.Waste_Weight_KG) as Total_Waste
    FROM Waste_Management wm
    GROUP BY Month
    ORDER BY Month
    """,
    
    "Transportation Distance by Vehicle Type": """
    SELECT Vehicle_Type, SUM(Distance_KM) as Total_Distance
    FROM Transportation
    GROUP BY Vehicle_Type
    ORDER BY Total_Distance DESC
    """,
    
    "Energy Source Distribution": """
    SELECT Energy_Source, COUNT(*) as Usage_Count, SUM(Consumption_KWH) as Total_KWH
    FROM Energy_Consumption
    GROUP BY Energy_Source
    ORDER BY Total_KWH DESC
    """,
    
    "Industry Emission by Location": """
    SELECT up.Location, SUM(ia.Emission_Produced) as Total_Emission
    FROM User_Profile up
    JOIN Industrial_Activity ia ON up.User_ID = ia.User_ID
    GROUP BY up.Location
    ORDER BY Total_Emission DESC
    """
} 