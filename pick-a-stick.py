"""
pick-a-stick.py
Helps you pick a cigar from a list of cigars (usually your humidor collection exported from cigarscanner.com)
This program will randomly pick out a cigar to save you from decision paralysis. It will also give you the option to filter by brand, size, and strength. I plan to add sommelier type recommendations in the future, but for now, this is a simple random picker.

Author/Maintainer: Mason
06/2026
"""

def main():
    import random
    import pandas as pd

    # Load the cigar data from a CSV file
    try:
        cigars_df = pd.read_csv('cigars.csv')
    except FileNotFoundError:
        print("Error: 'cigars.csv' file not found. Please ensure the file is in the same directory.")
        return

    # Display available filters
    print("Available filters:")
    print("1. Brand")
    print("2. Size")
    print("3. Strength")
    print("4. No filter (pick from all)")

    # Get user input for filtering
    filter_choice = input("Enter the number corresponding to your filter choice (or press Enter for no filter): ")

    if filter_choice == '1':
        brand = input("Enter the brand you want to filter by: ")
        filtered_cigars = cigars_df[cigars_df['Brand'].str.contains(brand, case=False, na=False)]
    elif filter_choice == '2':
        size = input("Enter the size you want to filter by: ")
        filtered_cigars = cigars_df[cigars_df['Size'].str.contains(size, case=False, na=False)]
    elif filter_choice == '3':
        strength = input("Enter the strength you want to filter by: ")
        filtered_cigars = cigars_df[cigars_df['Strength'].str.contains(strength, case=False, na=False)]
    else:
        filtered_cigars = cigars_df

    # Check if there are any cigars left after filtering
    if filtered_cigars.empty:
        print("No cigars found with the specified filter.")
        return

    # Randomly select a cigar from the filtered list
    selected_cigar = filtered_cigars.sample(n=1).iloc[0]
    
    # Display the selected cigar
    print("\nSelected Cigar:")
    print(f"Brand: {selected_cigar['Brand']}")
    print(f"Name: {selected_cigar['Name']}")
    print(f"Size: {selected_cigar['Size']}")
    print(f"Strength: {selected_cigar['Strength']}")