import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense, LayerNormalization, MultiHeadAttention, Dropout, GlobalAveragePooling1D
from sklearn.metrics import mean_squared_error
import math
import matplotlib.pyplot as plt

# Load and prepare the dataset
file_path = 'DATA/' + 'QCOM.csv'  # Make sure to have your dataset ready
df = pd.read_csv(file_path)
data = df[['Close']].values
scaler = MinMaxScaler(feature_range=(0, 1))
data_scaled = scaler.fit_transform(data)

def create_dataset(dataset, time_step=1):
    dataX, dataY = [], []
    for i in range(len(dataset) - time_step - 1):
        a = dataset[i:(i + time_step), 0]
        dataX.append(a)
        dataY.append(dataset[i + time_step, 0])
    return np.array(dataX), np.array(dataY)

# Parameters
time_step = 100
training_size = int(len(data_scaled) * 0.80)
test_size = len(data_scaled) - training_size
train_data, test_data = data_scaled[0:training_size,:], data_scaled[training_size:len(data_scaled),:]

X_train, y_train = create_dataset(train_data, time_step)
X_test, y_test = create_dataset(test_data, time_step)

# Reshape input for the model
X_train = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
X_test = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)

# Transformer Block
def transformer_encoder(inputs, head_size, num_heads, ff_dim, dropout=0):
    x = LayerNormalization(epsilon=1e-6)(inputs)
    x = MultiHeadAttention(key_dim=head_size, num_heads=num_heads, dropout=dropout)(x, x)
    x = Dropout(dropout)(x)
    res = x + inputs

    x = LayerNormalization(epsilon=1e-6)(res)
    x = Dense(ff_dim, activation="relu")(x)
    x = Dropout(dropout)(x)
    x = Dense(inputs.shape[-1])(x)
    return x + res

# Model Definition
inputs = Input(shape=(X_train.shape[1], X_train.shape[2]))
x = transformer_encoder(inputs, head_size=256, num_heads=4, ff_dim=4, dropout=0.1)
x = GlobalAveragePooling1D(data_format='channels_first')(x)
x = Dropout(0.1)(x)
x = Dense(20, activation="relu")(x)
outputs = Dense(1, activation="linear")(x)

model = Model(inputs=inputs, outputs=outputs)
model.compile(optimizer="adam", loss="mean_squared_error")

# Model Summary
model.summary()

# Train the model
model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=100, batch_size=64, verbose=1)

# Make predictions
train_predict = model.predict(X_train)
test_predict = model.predict(X_test)

# Inverse transform predictions
train_predict = scaler.inverse_transform(train_predict)
test_predict = scaler.inverse_transform(test_predict)

# Evaluate the model (Optional: Calculate RMSE or other metrics)
train_rmse = math.sqrt(mean_squared_error(y_train, scaler.inverse_transform(train_predict.reshape(-1, 1))))
test_rmse = math.sqrt(mean_squared_error(y_test, scaler.inverse_transform(test_predict.reshape(-1, 1))))

print(f"Train RMSE: {train_rmse}")
print(f"Test RMSE: {test_rmse}")

# Extend the test prediction
extend_steps = int(0.05 * len(data_scaled))
last_test_input = X_test[-1]

extended_predictions = []
for _ in range(extend_steps):
    pred = model.predict(last_test_input.reshape(1, time_step, 1))
    extended_predictions.append(pred[0, 0])
    last_test_input = np.append(last_test_input[1:], pred).reshape(time_step, 1)

# Inverse transform the extended predictions
extended_predictions = scaler.inverse_transform(np.array(extended_predictions).reshape(-1, 1))

# Concatenate the extended predictions to the test predictions
extended_test_predict = np.concatenate((test_predict, extended_predictions))

# Print shapes for debugging
print(f"Shape of data_scaled: {data_scaled.shape}")
print(f"Shape of train_predict: {train_predict.shape}")
print(f"Shape of test_predict: {test_predict.shape}")
print(f"Shape of extended_test_predict: {extended_test_predict.shape}")

# Adjust the time_step offset for plotting
trainPredictPlot = np.empty_like(data_scaled)
trainPredictPlot[:, :] = np.nan
trainPredictPlot[time_step:len(train_predict)+time_step, :] = train_predict

# Shift test predictions for plotting
testPredictPlot = np.empty((len(data_scaled) + extend_steps, 1))
testPredictPlot[:, :] = np.nan

# Calculate the correct indices for testPredictPlot
start_index = len(train_predict) + (time_step * 2) + 1
end_index = start_index + len(extended_test_predict)
testPredictPlot[start_index:end_index, :] = extended_test_predict

# Print the start and end indices for debugging
print(f"Start index for testPredictPlot: {start_index}")
print(f"End index for testPredictPlot: {end_index}")

# Plot baseline and predictions
plt.figure(figsize=(12, 6))
plt.plot(scaler.inverse_transform(data_scaled), label='Actual Stock Price')
plt.plot(trainPredictPlot, label='Train Predict')
plt.plot(testPredictPlot, label='Test Predict')
plt.title('Stock Price Prediction using Transformer with Extended Forecast')
plt.xlabel('Time')
plt.ylabel('Stock Price')
plt.legend()
plt.show()
