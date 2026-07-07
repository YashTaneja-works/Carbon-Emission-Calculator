updated_queries = {
    # Basic queries
    "View All Users": "SELECT * FROM User_Profile",
    "View All Transportation Records": "SELECT * FROM Transportation",
    "View All Energy Consumption Records": "SELECT * FROM Energy_Consumption",
    "View All Waste Management Records": "SELECT * FROM Waste_Management",
    "View All Industrial Activities": "SELECT * FROM Industrial_Activity",
    "View All Carbon Offsets": "SELECT * FROM Carbon_Offset",
    
    # Basic WHERE examples
    "View Users in New York": """
    SELECT * FROM User_Profile 
    WHERE Location = 'New York'
    """,
    
    "View Car Transportation Only": """
    SELECT * FROM Transportation 
    WHERE Vehicle_Type = 'Car'
    """,
    
    "View High Energy Consumption": """
    SELECT * FROM Energy_Consumption 
    WHERE Consumption_KWH > 300
    """,
    
    # JOIN queries
    "User Transportation Data": """
    SELECT up.User_ID, up.Full_Name, t.Vehicle_Type, t.Distance_KM, t.Date 
    FROM User_Profile up
    JOIN Transportation t ON up.User_ID = t.User_ID
    ORDER BY up.User_ID, t.Date
    """,
    
    "User Energy Consumption": """
    SELECT up.User_ID, up.Full_Name, ec.Energy_Source, ec.Consumption_KWH, ec.Date 
    FROM User_Profile up
    JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    ORDER BY up.User_ID, ec.Date
    """,
    
    "User Waste Management": """
    SELECT up.User_ID, up.Full_Name, wm.Waste_Type, wm.Waste_Weight_KG, wm.Date 
    FROM User_Profile up
    JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    ORDER BY up.User_ID, wm.Date
    """,
    
    # Aggregation queries
    "Total Transportation by User": """
    SELECT up.User_ID, up.Full_Name, COUNT(t.Transport_ID) as Trip_Count, 
           SUM(t.Distance_KM) as Total_Distance 
    FROM User_Profile up
    LEFT JOIN Transportation t ON up.User_ID = t.User_ID
    GROUP BY up.User_ID
    ORDER BY Total_Distance DESC
    """,
    
    "Total Energy by User": """
    SELECT up.User_ID, up.Full_Name, COUNT(ec.Energy_ID) as Record_Count, 
           SUM(ec.Consumption_KWH) as Total_KWH 
    FROM User_Profile up
    LEFT JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    GROUP BY up.User_ID
    ORDER BY Total_KWH DESC
    """,
    
    "Total Waste by User": """
    SELECT up.User_ID, up.Full_Name, COUNT(wm.Waste_ID) as Waste_Count, 
           SUM(wm.Waste_Weight_KG) as Total_Weight 
    FROM User_Profile up
    LEFT JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    GROUP BY up.User_ID
    ORDER BY Total_Weight DESC
    """,
    
    # More complex queries
    "Transportation by Vehicle Type": """
    SELECT Vehicle_Type, COUNT(*) as Trip_Count, 
           SUM(Distance_KM) as Total_Distance,
           AVG(Distance_KM) as Average_Distance
    FROM Transportation
    GROUP BY Vehicle_Type
    ORDER BY Total_Distance DESC
    """,
    
    "Energy by Source Type": """
    SELECT Energy_Source, COUNT(*) as Record_Count, 
           SUM(Consumption_KWH) as Total_KWH,
           AVG(Consumption_KWH) as Average_KWH
    FROM Energy_Consumption
    GROUP BY Energy_Source
    ORDER BY Total_KWH DESC
    """,
    
    "Waste by Type": """
    SELECT Waste_Type, COUNT(*) as Waste_Count, 
           SUM(Waste_Weight_KG) as Total_Weight,
           AVG(Waste_Weight_KG) as Average_Weight
    FROM Waste_Management
    GROUP BY Waste_Type
    ORDER BY Total_Weight DESC
    """,
    
    # Date-based queries
    "Transport by Month": """
    SELECT strftime('%Y-%m', Date) as Month, 
           COUNT(*) as Trip_Count, 
           SUM(Distance_KM) as Total_Distance
    FROM Transportation
    GROUP BY Month
    ORDER BY Month
    """,
    
    "Energy Consumption by Month": """
    SELECT strftime('%Y-%m', Date) as Month, 
           SUM(Consumption_KWH) as Total_KWH
    FROM Energy_Consumption
    GROUP BY Month
    ORDER BY Month
    """,
    
    "Waste Generation by Month": """
    SELECT strftime('%Y-%m', Date) as Month, 
           SUM(Waste_Weight_KG) as Total_Waste
    FROM Waste_Management
    GROUP BY Month
    ORDER BY Month
    """,
    
    # Subqueries
    "Users with Above Average Energy Use": """
    SELECT up.User_ID, up.Full_Name, SUM(ec.Consumption_KWH) as Total_KWH
    FROM User_Profile up
    JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    GROUP BY up.User_ID
    HAVING Total_KWH > (
        SELECT AVG(Total_User_KWH) 
        FROM (
            SELECT SUM(Consumption_KWH) as Total_User_KWH
            FROM Energy_Consumption
            GROUP BY User_ID
        )
    )
    ORDER BY Total_KWH DESC
    """,
    
    "Users with Below Average Waste": """
    SELECT up.User_ID, up.Full_Name, SUM(wm.Waste_Weight_KG) as Total_Waste
    FROM User_Profile up
    JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    GROUP BY up.User_ID
    HAVING Total_Waste < (
        SELECT AVG(Total_User_Waste) 
        FROM (
            SELECT SUM(Waste_Weight_KG) as Total_User_Waste
            FROM Waste_Management
            GROUP BY User_ID
        )
    )
    ORDER BY Total_Waste
    """,
    
    # Multi-table Join
    "User Environmental Impact Summary": """
    SELECT up.User_ID, up.Full_Name, up.Location,
           SUM(t.Distance_KM) as Total_Travel_Distance,
           SUM(ec.Consumption_KWH) as Total_Energy_Consumption,
           SUM(wm.Waste_Weight_KG) as Total_Waste_Generated,
           SUM(ia.Emission_Produced) as Total_Industrial_Emissions,
           SUM(co.Offset_Amount) as Total_Carbon_Offset
    FROM User_Profile up
    LEFT JOIN Transportation t ON up.User_ID = t.User_ID
    LEFT JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    LEFT JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    LEFT JOIN Industrial_Activity ia ON up.User_ID = ia.User_ID
    LEFT JOIN Carbon_Offset co ON up.User_ID = co.User_ID
    GROUP BY up.User_ID
    ORDER BY up.User_ID
    """,
    
    # CREATE VIEW Example (shown as SELECT)
    "User Carbon Footprint View": """
    SELECT up.User_ID, up.Full_Name,
           COALESCE(SUM(t.Distance_KM * ef_t.Emission_Per_Unit), 0) as Transport_Emissions,
           COALESCE(SUM(ec.Consumption_KWH * ef_e.Emission_Per_Unit), 0) as Energy_Emissions,
           COALESCE(SUM(wm.Waste_Weight_KG * ef_w.Emission_Per_Unit), 0) as Waste_Emissions,
           COALESCE(SUM(ia.Emission_Produced), 0) as Industrial_Emissions,
           COALESCE(SUM(co.Offset_Amount), 0) as Carbon_Offset
    FROM User_Profile up
    LEFT JOIN Transportation t ON up.User_ID = t.User_ID
    LEFT JOIN Emission_Factor ef_t ON t.Vehicle_Type = ef_t.Source_Type
    LEFT JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    LEFT JOIN Emission_Factor ef_e ON ec.Energy_Source = ef_e.Source_Type
    LEFT JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    LEFT JOIN Emission_Factor ef_w ON 'Waste' = ef_w.Source_Type
    LEFT JOIN Industrial_Activity ia ON up.User_ID = ia.User_ID
    LEFT JOIN Carbon_Offset co ON up.User_ID = co.User_ID
    GROUP BY up.User_ID
    """,
    
    # INSERT Example (shown as SELECT)
    "New User Template": """
    -- Example: 
    -- INSERT INTO User_Profile (Full_Name, Email, Location) 
    -- VALUES ('New User', 'new.user@email.com', 'City')
    SELECT 'INSERT INTO User_Profile (Full_Name, Email, Location) VALUES (''New User'', ''new.user@email.com'', ''City'')' as SQL_Statement
    """,
    
    # UPDATE Example (shown as SELECT)
    "Update User Template": """
    -- Example:
    -- UPDATE User_Profile 
    -- SET Email = 'updated.email@example.com', Location = 'New Location' 
    -- WHERE User_ID = 1
    SELECT 'UPDATE User_Profile SET Email = ''updated.email@example.com'', Location = ''New Location'' WHERE User_ID = 1' as SQL_Statement
    """,
    
    # DELETE Example (shown as SELECT)
    "Delete Record Template": """
    -- Example:
    -- DELETE FROM Transportation 
    -- WHERE Transport_ID = 1
    SELECT 'DELETE FROM Transportation WHERE Transport_ID = 1' as SQL_Statement
    """,
    
    # NEW ADVANCED QUERIES
    
    # View creation and usage example
    "Create Carbon Footprint View": """
    -- First create the view
    CREATE VIEW IF NOT EXISTS Carbon_Footprint_View AS
    SELECT 
        up.User_ID, 
        up.Full_Name,
        up.Location,
        COALESCE(SUM(t.Distance_KM * ef_t.Emission_Per_Unit), 0) as Transport_Emissions,
        COALESCE(SUM(ec.Consumption_KWH * ef_e.Emission_Per_Unit), 0) as Energy_Emissions,
        COALESCE(SUM(wm.Waste_Weight_KG * ef_w.Emission_Per_Unit), 0) as Waste_Emissions,
        COALESCE(SUM(ia.Emission_Produced), 0) as Industrial_Emissions,
        COALESCE(SUM(co.Offset_Amount), 0) as Offset_Amount,
        (
            COALESCE(SUM(t.Distance_KM * ef_t.Emission_Per_Unit), 0) +
            COALESCE(SUM(ec.Consumption_KWH * ef_e.Emission_Per_Unit), 0) +
            COALESCE(SUM(wm.Waste_Weight_KG * ef_w.Emission_Per_Unit), 0) +
            COALESCE(SUM(ia.Emission_Produced), 0) -
            COALESCE(SUM(co.Offset_Amount), 0)
        ) as Net_Emissions
    FROM User_Profile up
    LEFT JOIN Transportation t ON up.User_ID = t.User_ID
    LEFT JOIN Emission_Factor ef_t ON t.Vehicle_Type = ef_t.Source_Type
    LEFT JOIN Energy_Consumption ec ON up.User_ID = ec.User_ID
    LEFT JOIN Emission_Factor ef_e ON ec.Energy_Source = ef_e.Source_Type
    LEFT JOIN Waste_Management wm ON up.User_ID = wm.User_ID
    LEFT JOIN Emission_Factor ef_w ON 'Waste' = ef_w.Source_Type
    LEFT JOIN Industrial_Activity ia ON up.User_ID = ia.User_ID
    LEFT JOIN Carbon_Offset co ON up.User_ID = co.User_ID
    GROUP BY up.User_ID;
    
    -- Then select from the view
    SELECT * FROM Carbon_Footprint_View;
    """,
    
    "Query Carbon Footprint View": """
    SELECT * FROM Carbon_Footprint_View
    ORDER BY Net_Emissions DESC;
    """,
    
    # Complex nested subquery with EXISTS
    "Users with No Carbon Offset": """
    SELECT up.User_ID, up.Full_Name, up.Email, up.Location
    FROM User_Profile up
    WHERE NOT EXISTS (
        SELECT 1 
        FROM Carbon_Offset co 
        WHERE co.User_ID = up.User_ID
    )
    AND EXISTS (
        SELECT 1 
        FROM (
            SELECT t.User_ID FROM Transportation t 
            UNION
            SELECT ec.User_ID FROM Energy_Consumption ec
            UNION
            SELECT wm.User_ID FROM Waste_Management wm
            UNION
            SELECT ia.User_ID FROM Industrial_Activity ia
        ) as active_users
        WHERE active_users.User_ID = up.User_ID
    )
    ORDER BY up.User_ID;
    """,
    
    # CASE statement with window functions
    "User Emission Categories with Ranking": """
    SELECT 
        User_ID, 
        Full_Name,
        Net_Emissions,
        CASE 
            WHEN Net_Emissions > 1000 THEN 'Very High'
            WHEN Net_Emissions > 500 THEN 'High'
            WHEN Net_Emissions > 200 THEN 'Medium'
            WHEN Net_Emissions > 0 THEN 'Low'
            ELSE 'Carbon Negative'
        END as Emission_Category,
        RANK() OVER (ORDER BY Net_Emissions DESC) as Emission_Rank,
        PERCENT_RANK() OVER (ORDER BY Net_Emissions DESC) as Percentile
    FROM Carbon_Footprint_View
    ORDER BY Net_Emissions DESC;
    """,
    
    # Common Table Expressions (CTE)
    "Emission Analysis with CTE": """
    WITH 
    UserEmissions AS (
        SELECT 
            up.User_ID, 
            up.Full_Name,
            COALESCE(SUM(t.Distance_KM * ef.Emission_Per_Unit), 0) as Transport_Emissions
        FROM User_Profile up
        LEFT JOIN Transportation t ON up.User_ID = t.User_ID
        LEFT JOIN Emission_Factor ef ON t.Vehicle_Type = ef.Source_Type
        GROUP BY up.User_ID
    ),
    EmissionStats AS (
        SELECT 
            AVG(Transport_Emissions) as Avg_Emissions,
            MAX(Transport_Emissions) as Max_Emissions,
            MIN(Transport_Emissions) as Min_Emissions
        FROM UserEmissions
        WHERE Transport_Emissions > 0
    )
    SELECT 
        ue.User_ID,
        ue.Full_Name,
        ue.Transport_Emissions,
        es.Avg_Emissions,
        ((ue.Transport_Emissions - es.Avg_Emissions) / es.Avg_Emissions) * 100 as Percent_Diff_From_Avg,
        CASE 
            WHEN ue.Transport_Emissions > es.Avg_Emissions THEN 'Above Average'
            WHEN ue.Transport_Emissions < es.Avg_Emissions THEN 'Below Average'
            ELSE 'Average'
        END as Emissions_Category
    FROM UserEmissions ue, EmissionStats es
    WHERE ue.Transport_Emissions > 0
    ORDER BY ue.Transport_Emissions DESC;
    """,
    
    # UNION, INTERSECT, EXCEPT example
    "Users Activity Comparison": """
    -- Users with transportation but no energy consumption
    SELECT up.User_ID, up.Full_Name, 'Transportation Only' as Activity_Type
    FROM User_Profile up
    WHERE EXISTS (
        SELECT 1 FROM Transportation t WHERE t.User_ID = up.User_ID
    )
    AND NOT EXISTS (
        SELECT 1 FROM Energy_Consumption ec WHERE ec.User_ID = up.User_ID
    )
    
    UNION
    
    -- Users with energy consumption but no transportation
    SELECT up.User_ID, up.Full_Name, 'Energy Only' as Activity_Type
    FROM User_Profile up
    WHERE EXISTS (
        SELECT 1 FROM Energy_Consumption ec WHERE ec.User_ID = up.User_ID
    )
    AND NOT EXISTS (
        SELECT 1 FROM Transportation t WHERE t.User_ID = up.User_ID
    )
    
    UNION
    
    -- Users with both
    SELECT up.User_ID, up.Full_Name, 'Both Activities' as Activity_Type
    FROM User_Profile up
    WHERE EXISTS (
        SELECT 1 FROM Transportation t WHERE t.User_ID = up.User_ID
    )
    AND EXISTS (
        SELECT 1 FROM Energy_Consumption ec WHERE ec.User_ID = up.User_ID
    )
    
    ORDER BY User_ID;
    """,
    
    # Self-join example
    "Compare Users in Same Location": """
    SELECT 
        u1.User_ID as User1_ID, 
        u1.Full_Name as User1_Name,
        u2.User_ID as User2_ID,
        u2.Full_Name as User2_Name,
        u1.Location,
        cfv1.Net_Emissions as User1_Emissions,
        cfv2.Net_Emissions as User2_Emissions,
        ABS(cfv1.Net_Emissions - cfv2.Net_Emissions) as Emission_Difference
    FROM User_Profile u1
    JOIN User_Profile u2 ON u1.Location = u2.Location AND u1.User_ID < u2.User_ID
    JOIN Carbon_Footprint_View cfv1 ON u1.User_ID = cfv1.User_ID
    JOIN Carbon_Footprint_View cfv2 ON u2.User_ID = cfv2.User_ID
    ORDER BY u1.Location, Emission_Difference DESC;
    """,
    
    # Recursive CTE example
    "Emission Reduction Projection": """
    WITH RECURSIVE 
    EmissionProjection AS (
        -- Base case: current emissions
        SELECT 
            User_ID, 
            Full_Name, 
            Net_Emissions as Current_Emissions,
            Net_Emissions as Projected_Emissions,
            0 as Year
        FROM Carbon_Footprint_View
        
        UNION ALL
        
        -- Recursive case: reduce by 5% each year
        SELECT 
            User_ID, 
            Full_Name, 
            Current_Emissions,
            Projected_Emissions * 0.95 as Projected_Emissions,
            Year + 1
        FROM EmissionProjection
        WHERE Year < 10  -- Project for 10 years
    )
    SELECT 
        User_ID, 
        Full_Name, 
        Current_Emissions,
        Year,
        ROUND(Projected_Emissions, 2) as Projected_Emissions,
        ROUND((Projected_Emissions / Current_Emissions) * 100, 2) as Percent_Of_Original
    FROM EmissionProjection
    WHERE User_ID IN (
        SELECT User_ID FROM Carbon_Footprint_View 
        ORDER BY Net_Emissions DESC LIMIT 3  -- Only show top 3 emitters
    )
    ORDER BY User_ID, Year;
    """
} 