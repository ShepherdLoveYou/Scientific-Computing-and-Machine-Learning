"""
Handwritten Digit Classification using Multi-Layer Perception and Keras / 使用多层感知机 + Keras 做手写数字分类
MNIST

Requires Keras 3 and a backend (torch / jax / tensorflow). This is NOT
installed in the default slim image — if you want to execute this reference
implementation, run:

    pip install keras torch

and then:

    KERAS_BACKEND=torch python DigitsClassification-MLP_Keras.py
"""
import os
import time

# Default to the PyTorch backend when the env var is not set by the user.
os.environ.setdefault("KERAS_BACKEND", "torch")

import numpy as np
import keras
from keras import layers
from keras.datasets import mnist

(X_train, y_train), (X_test, y_test) = mnist.load_data("mnist.npz")

# Scale images to the [0, 1] range
X_train = X_train.astype("float32") / 255
X_test = X_test.astype("float32") / 255
# Reshape to 28 x 28 pixels = 784 features
X_train = X_train.reshape(X_train.shape[0], 784)
X_test = X_test.reshape(X_test.shape[0], 784)

num_classes = 10
# convert class vectors to binary class matrices
y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)

model = keras.Sequential(
    [
        keras.Input(shape=(784,)),
        layers.Dense(30, activation="sigmoid"),
        layers.Dense(30, activation="sigmoid"),
        layers.Dense(num_classes, activation="softmax"),
    ]
)
model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])

batch_size = 20
epochs = 10
time_start = time.time()
model.fit(X_train, y_train, batch_size=batch_size, epochs=epochs, validation_split=0.1)
time_end = time.time()
print("Times Used %.2f S" % (time_end - time_start))

score = model.evaluate(X_test, y_test, verbose=0)
print("Test loss:", score[0])
print("Test accuracy:", score[1])
