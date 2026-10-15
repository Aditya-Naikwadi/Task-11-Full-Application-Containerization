"""
=============================================================================
TASK 15: DEEP LEARNING MODEL TRAINING PIPELINE (train.py)
=============================================================================
Author: Aditya Naikwadi
Role: Lead Data Scientist & MLOps Architect
Evaluation Platform: L&T Edutech LMS Platform

Deliverable:
  - Serialized Trained Model: 'api/model.h5'
  - Performance Evaluation Plot: 'training_performance.png'
=============================================================================
"""

import os
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt

# Suppress verbose TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (train.py) %(message)s"
)
logger = logging.getLogger(__name__)

# Enforce deterministic reproducibility
SEED = 42
np.random.seed(SEED)
tf.random.set_seed(SEED)

# Hyperparameters
NUM_SAMPLES = 2500
EXPECTED_FEATURES = 4
NUM_CLASSES = 3
CLASS_NAMES = ["Class 0 (Low Risk)", "Class 1 (Moderate Risk)", "Class 2 (High Risk)"]
BATCH_SIZE = 32
EPOCHS = 30

MODEL_EXPORT_PATH = os.path.join(os.path.dirname(__file__), "api", "model.h5")
METRICS_PLOT_PATH = os.path.join(os.path.dirname(__file__), "training_performance.png")


def generate_synthetic_clinical_data(n_samples=2500):
    """
    Synthesizes normalized numerical clinical feature vectors matching
    the Flask API and Streamlit UI schema (Glucose, Blood Pressure, BMI, Age).
    """
    logger.info(f"Generating clinical feature vectors ({n_samples} samples)...")
    # Features: [Glucose (70-200), Blood Pressure (60-140), BMI (18-45), Age (18-80)]
    f1 = np.random.normal(100, 25, (n_samples, 1))  # Glucose
    f2 = np.random.normal(80, 15, (n_samples, 1))   # Blood Pressure
    f3 = np.random.normal(27, 6, (n_samples, 1))    # BMI
    f4 = np.random.normal(45, 15, (n_samples, 1))   # Age

    X = np.hstack([f1, f2, f3, f4])

    # Class assignment based on clinical risk indicators
    risk_score = (f1 - 70) * 0.4 + (f2 - 60) * 0.3 + (f3 - 18) * 1.5 + (f4 - 18) * 0.5
    y = np.zeros(n_samples, dtype=np.int32)
    y[risk_score[:, 0] > 60] = 1
    y[risk_score[:, 0] > 95] = 2

    # Normalize inputs
    mean = np.mean(X, axis=0)
    std = np.std(X, axis=0) + 1e-7
    X = (X - mean) / std

    # Partition dataset: 70% Train, 15% Validation, 15% Holdout Test
    n_train = int(0.70 * n_samples)
    n_val = int(0.15 * n_samples)

    X_train, y_train = X[:n_train], y[:n_train]
    X_val, y_val = X[n_train:n_train + n_val], y[n_train:n_train + n_val]
    X_test, y_test = X[n_train + n_val:], y[n_train + n_val:]

    logger.info(f"Dataset Split: Train={len(X_train)} | Val={len(X_val)} | Test={len(X_test)}")
    return (X_train, y_train), (X_val, y_val), (X_test, y_test)


def build_deep_learning_classifier():
    """
    Constructs a Deep Neural Network classifier with BatchNormalization,
    Dropout regularization, and a Softmax multi-class output head.
    """
    logger.info("Constructing Deep Neural Network Architecture...")
    model = models.Sequential([
        layers.Input(shape=(EXPECTED_FEATURES,)),
        layers.Dense(64, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.2),

        layers.Dense(32, activation="relu"),
        layers.BatchNormalization(),
        layers.Dropout(0.2),

        layers.Dense(16, activation="relu"),
        layers.BatchNormalization(),

        layers.Dense(NUM_CLASSES, activation="softmax", name="prediction_probabilities")
    ])

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.005),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    model.summary(print_fn=logger.info)
    return model


def train_and_evaluate():
    # 1. Load Data
    (X_train, y_train), (X_val, y_val), (X_test, y_test) = generate_synthetic_clinical_data(NUM_SAMPLES)

    # 2. Build Model
    model = build_deep_learning_classifier()

    # Ensure api directory exists
    os.makedirs(os.path.dirname(MODEL_EXPORT_PATH), exist_ok=True)

    # 3. Configure MLOps Callbacks
    callbacks = [
        ModelCheckpoint(
            filepath=MODEL_EXPORT_PATH,
            monitor="val_accuracy",
            mode="max",
            save_best_only=True,
            verbose=1
        ),
        EarlyStopping(
            monitor="val_loss",
            patience=6,
            restore_best_weights=True,
            verbose=1
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-5,
            verbose=1
        )
    ]

    # 4. Train Model
    logger.info("Initiating model training across epochs...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1
    )

    # 5. Evaluate Generalization against Holdout Test Set
    logger.info("Evaluating holdout test set generalization...")
    test_loss, test_accuracy = model.evaluate(X_test, y_test, verbose=0)
    logger.info("=" * 60)
    logger.info(f"FINAL METRICS: Test Loss = {test_loss:.4f} | Test Accuracy = {test_accuracy * 100:.2f}%")
    logger.info("=" * 60)

    # Explicit fallback save if checkpoint did not trigger
    if not os.path.exists(MODEL_EXPORT_PATH):
        model.save(MODEL_EXPORT_PATH)
        logger.info(f"Saved model fallback to {MODEL_EXPORT_PATH}")

    # 6. Generate and Export Performance Evaluation Plot
    plot_training_curves(history, test_accuracy, test_loss)

    return test_loss, test_accuracy


def plot_training_curves(history, test_acc, test_loss):
    """Generates dual-plot diagnostic curves for documentation."""
    acc = history.history["accuracy"]
    val_acc = history.history["val_accuracy"]
    loss = history.history["loss"]
    val_loss = history.history["val_loss"]
    epochs_range = range(1, len(acc) + 1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Accuracy Plot
    ax1.plot(epochs_range, acc, label="Training Accuracy", color="#1E3A8A", linewidth=2.2)
    ax1.plot(epochs_range, val_acc, label="Validation Accuracy", color="#3B82F6", linewidth=2.2, linestyle="--")
    ax1.axhline(y=test_acc, color="#10B981", linestyle=":", linewidth=2, label=f"Test Accuracy ({test_acc*100:.1f}%)")
    ax1.set_title("Deep Learning Model Accuracy Across Epochs", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Epochs")
    ax1.set_ylabel("Accuracy")
    ax1.legend(loc="lower right")
    ax1.grid(True, linestyle=":", alpha=0.6)

    # Loss Plot
    ax2.plot(epochs_range, loss, label="Training Loss", color="#B91C1C", linewidth=2.2)
    ax2.plot(epochs_range, val_loss, label="Validation Loss", color="#EF4444", linewidth=2.2, linestyle="--")
    ax2.axhline(y=test_loss, color="#F59E0B", linestyle=":", linewidth=2, label=f"Test Loss ({test_loss:.4f})")
    ax2.set_title("Categorical Cross-Entropy Loss Across Epochs", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Epochs")
    ax2.set_ylabel("Loss")
    ax2.legend(loc="upper right")
    ax2.grid(True, linestyle=":", alpha=0.6)

    plt.tight_layout()
    plt.savefig(METRICS_PLOT_PATH, dpi=300)
    logger.info(f"Performance plot successfully generated at: {METRICS_PLOT_PATH}")
    plt.close()


if __name__ == "__main__":
    train_and_evaluate()
