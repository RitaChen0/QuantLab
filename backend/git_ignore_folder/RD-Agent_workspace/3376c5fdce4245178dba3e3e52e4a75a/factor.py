import pandas as pd
import numpy as np
import h5py

# Function to calculate the 20-day Simple Moving Average (SMA)
def calculate_20DaySMA(data):
    # Ensure the data is sorted by datetime
    data = data.sort_index()
    # Calculate the 20-day SMA
    data['20DaySMA'] = data['close'].rolling(window=20).mean()
    return data[['20DaySMA']]

if __name__ == '__main__':
    # Load your dataset here
    # Example: data = pd.read_csv('your_data.csv', index_col=[0, 1], parse_dates=True)
    data = pd.read_csv('price_data.csv', index_col='datetime', parse_dates=True)
    data = data.pivot(columns='instrument', values='close')

    # Calculate the 20DaySMA
    result = calculate_20DaySMA(data)

    # Save the result to a HDF5 file
    with h5py.File('result.h5', 'w') as f:
        result.to_hdf(f, key='data', mode='w')
