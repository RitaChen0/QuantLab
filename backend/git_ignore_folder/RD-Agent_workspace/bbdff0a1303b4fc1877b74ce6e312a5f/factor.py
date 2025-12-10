import pandas as pd
import numpy as np

# Function to calculate the 20-day Simple Moving Average (SMA)
def calculate_20_day_SMA(df):
    # Calculate the 20-day SMA for the closing prices
    df['20_day_SMA'] = df['close'].rolling(window=20, min_periods=1).mean()
    # Return only the 20_day_SMA column
    return df[['20_day_SMA']]

# Main function to be executed
if __name__ == '__main__':
    # Load sample data
    data = {'datetime': pd.date_range(start='2020-01-01', periods=100, freq='D'),
            'instrument': ['stock']*100,
            'close': np.random.rand(100) * 100}
    df = pd.DataFrame(data).set_index(['datetime', 'instrument'])
    
    # Calculate the 20-day SMA
    result_df = calculate_20_day_SMA(df)
    
    # Save the result to a HDF5 file
    result_df.to_hdf('result.h5', key='data', mode='w', format='table')
    print('Calculation is complete and the results are saved to result.h5.')