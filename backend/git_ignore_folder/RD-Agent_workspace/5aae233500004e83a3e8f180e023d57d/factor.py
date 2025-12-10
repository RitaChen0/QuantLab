import pandas as pd
import numpy as np
import h5py

# Function to calculate the VolumeShock3D factor
def calculate_volumeshock3d(data):
    # Calculate the sum of volumes for the last 3 days and the previous 3 days
    recent_volume = data.rolling(window=3).sum()
    previous_volume = data.shift(3).rolling(window=3).sum()

    # Calculate Volume Shock
    volume_shock = (recent_volume - previous_volume) / previous_volume
    volume_shock = volume_shock.rename('VolumeShock3D')
    return volume_shock

# Main function to run the calculation
if __name__ == '__main__':
    # Sample data loading (to be replaced with actual data loading code)
    # data = pd.read_csv('path_to_data.csv', index_col=["datetime", "instrument"])
    # For demonstration, creating a sample dataframe
    dates = pd.date_range(start='2020-01-01', periods=100)
    instruments = ['SH600000', 'SZ300059']
    data = pd.DataFrame(data=np.random.randint(10000, 100000, size=(100, 2)), index=dates, columns=instruments)

    # Calculating the factor
    result = calculate_volumeshock3d(data)

    # Saving the result to a HDF5 file
    with pd.HDFStore('result.h5', 'w') as store:
        store.put('VolumeShock3D', result, format='table', data_columns=True)