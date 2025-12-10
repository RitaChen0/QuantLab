import pandas as pd
import numpy as np
import h5py

# Function to calculate the 30-day Simple Moving Average (SMA)
def calculate_30DaySMA(data):
    # Calculate the rolling mean for the last 30 days
    return data['close'].rolling(window=30).mean()

# Main function to execute the calculation
if __name__ == '__main__':
    # Load data assuming it is stored in a CSV file named 'data.csv'
    data = pd.read_csv('data.csv', parse_dates=['datetime'], index_col=['datetime', 'instrument'])
    
    # Calculate the 30DaySMA
    data['30DaySMA'] = calculate_30DaySMA(data)
    
    # Prepare the result DataFrame
    result = data[['30DaySMA']].dropna()
    
    # Save the results to a HDF5 file
    with pd.HDFStore('result.h5') as store:
        store.put('data', result, format='table')

    print('Calculation completed and results saved to result.h5.')