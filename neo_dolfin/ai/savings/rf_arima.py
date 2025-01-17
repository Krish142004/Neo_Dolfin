# -*- coding: utf-8 -*-
"""RF-ARIMA.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/15MtzxEwYyI_HnULJvT1qaiGsX7ZxtrX6
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import itertools
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from google.colab import drive
drive.mount('/content/drive')

dataset_path = "/content/drive/MyDrive/Colab_Notebooks/DataBytes Files/transaction_ut.csv"

data = pd.read_csv(dataset_path)

data.head(3)

duplicate_ids = data.duplicated(subset=['id'], keep=False)
duplicate_ids.sum()

# Drop unwanted columns from the dataset
df = data.drop(['type', 'id', 'status', 'direction', 'subClass_title', 'subClass_code',  'description', 'institution',], axis=1)

df.info()

df = df.sort_values(by="postDate")
# remove the "Z" from the datetime strings
df["postDate"] = df["postDate"].str.replace("Z", "")

# convert to datetime with the correct format
df["postDate"] = pd.to_datetime(df["postDate"], format="%Y-%m-%dT%H:%M:%S")

# new columns for postDate
df["Year"] = df["postDate"].dt.year
df["Month"] = df["postDate"].dt.month
df["Day"] = df["postDate"].dt.day
df["Hour"] = df["postDate"].dt.hour
df["Minute"] = df["postDate"].dt.minute
df["Second"] = df["postDate"].dt.second
df["DayOfWeek"] = df["postDate"].dt.dayofweek

"""No null values in the dataset"""

sns.kdeplot(df['amount'], shade=True)

df_date = pd.DataFrame({'Date': df['postDate'], 'Amount': df['amount'], 'DOW':df['DayOfWeek'], 'Month': df['Month']})

df_date['Date'] = pd.to_datetime(df_date['Date']).dt.date

df_date['Daily Balance'] = df_date.groupby('Date')['Amount'].cumsum()

df_date['Date'] = pd.to_datetime(df_date['Date'])
df_date.set_index('Date', inplace=True)
df_date = df_date[~df_date.index.duplicated(keep='first')]
# Then, resample the DataFrame with daily frequency and forward-fill missing values
df_date = df_date.resample('D').ffill()

# Reset the index to have 'postDate' as a regular column again
df_date.reset_index(inplace=True)

# plotting amount over timestamp
plt.figure(figsize=(10, 6))
plt.plot(df_date['Date'], df_date['Daily Balance'], marker='o', linestyle='--')

plt.xlabel('Date')
plt.ylabel('Daily Balance')
plt.title('Daily Balance Over Time')
plt.show()

# Split data into train and validation sets
train_fraction = 0.70
n = len(df)
train_df = df_date[:int(n*train_fraction)]
val_df = df_date[int(n*train_fraction):]

# Prepare data for training
X_train = train_df.drop(['Daily Balance','Date'], axis=1)
y_train = train_df['Daily Balance']
X_val = val_df.drop(['Daily Balance','Date'], axis=1)
y_val = val_df['Daily Balance']

#RF Model

rf_model = RandomForestRegressor(n_estimators=100)
rf_model.fit(X_train, y_train)

train_df.set_index('Date', inplace=True)

#ARIMA Model
daily_balance_time_series = train_df['Daily Balance']  #daily balance time series

#p,d,q value identification
p = d = q = range(0, 3)
pdq = list(itertools.product(p, d, q))
best_aic = np.inf
best_pdq = None

for param in pdq:
    try:
        arima_model = ARIMA(daily_balance_time_series, order=param)
        arima_result = arima_model.fit()
        if arima_result.aic < best_aic:
            best_aic = arima_result.aic
            best_pdq = param
    except:
        continue

#fitting ARIMA with best pdq values

arima_model = ARIMA(daily_balance_time_series, order=best_pdq)
arima_result = arima_model.fit()

#Hybrid Model

hybrid_predictions = []
rf_pred = []
AR_pred = []
for i in range(len(X_val)):
    #Random Forest
    rf_prediction = rf_model.predict([X_val.iloc[i]])[0]
    rf_pred.append(rf_prediction)

    #ARIMA
    arima_prediction = arima_result.forecast(steps=1)[0]  # Extract the forecasted value
    AR_pred.append(arima_prediction)

    # Estimate savings using predicted transaction amount and daily balance
    savings_prediction = rf_prediction - arima_prediction

    hybrid_predictions.append(savings_prediction)

mae = mean_absolute_error(y_val, hybrid_predictions)
print("Mean Absolute Error:", mae)

pd.DataFrame({'Actual': y_val, 'Prediction': hybrid_predictions, 'RF-Pred': rf_pred, 'ARIMA-Pred': AR_pred})

x_values = range(1, len(y_val) + 1)
plt.plot(x_values,y_val, 'b')
plt.plot(x_values,hybrid_predictions, 'r')

