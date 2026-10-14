import os
import logging
import numpy as np
from flask import Flask, request, jsonify
import tensorflow as tf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.h5")
EXPECTED_FEATURES = 4
CLASS_NAMES = ["Class 0 (Low Risk)", "Class 1 (Moderate Risk)", "Class 2 (High Risk)"]

def load_or_initialize_model():
    """
    Loads pre-trained model.h5 if available; otherwise initializes
    a baseline Keras model, saves it, and returns it.
    """
    if os.path.exists(MODEL_PATH):
        try:
            logger.info(f"Loading pre-trained model from {MODEL_PATH}...")
            loaded_model = tf.keras.models.load_model(MODEL_PATH)
            logger.info("Model loaded successfully.")
            return loaded_model
        except Exception as e:
            logger.warning(f"Could not load existing {MODEL_PATH}: {e}. Initializing a new model...")

    logger.info("Initializing baseline deep learning model...")
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(EXPECTED_FEATURES,)),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(8, activation="relu"),
        tf.keras.layers.Dense(len(CLASS_NAMES), activation="softmax")
    ])
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )
    try:
        model.save(MODEL_PATH)
        logger.info(f"Baseline model saved to {MODEL_PATH}.")
    except Exception as e:
        logger.warning(f"Could not save baseline model to {MODEL_PATH}: {e}")
    return model

# Global model instance loaded at startup
model = load_or_initialize_model()


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Docker container verification."""
    return jsonify({
        "status": "healthy",
        "model_loaded": model is not None
    }), 200


@app.route("/predict", methods=["POST"])
def predict():
    """
    Inference endpoint accepting JSON POST requests.
    Expected JSON structure:
      {
        "features": [value1, value2, value3, value4]
      }
      or batch format:
      {
        "features": [[v1, v2, v3, v4], ...]
      }
    """
    if not request.is_json:
        return jsonify({
            "status": "error",
            "message": "Invalid Content-Type. Request must be JSON (application/json)."
        }), 400

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({
            "status": "error",
            "message": "Malformed JSON payload in request."
        }), 400

    if "features" not in payload:
        return jsonify({
            "status": "error",
            "message": "Missing 'features' field in JSON payload."
        }), 400

    raw_features = payload["features"]

    # Preprocessing and validation
    try:
        data_array = np.array(raw_features, dtype=np.float32)

        # Handle single sample [f1, f2, f3, f4] -> reshape to (1, 4)
        if data_array.ndim == 1:
            if data_array.shape[0] != EXPECTED_FEATURES:
                return jsonify({
                    "status": "error",
                    "message": f"Feature dimension mismatch. Expected {EXPECTED_FEATURES} features, got {data_array.shape[0]}."
                }), 400
            data_array = np.expand_dims(data_array, axis=0)

        # Handle batch samples [[f1, f2, f3, f4], ...]
        elif data_array.ndim == 2:
            if data_array.shape[1] != EXPECTED_FEATURES:
                return jsonify({
                    "status": "error",
                    "message": f"Feature dimension mismatch. Expected {EXPECTED_FEATURES} features per row, got {data_array.shape[1]}."
                }), 400
        else:
            return jsonify({
                "status": "error",
                "message": "Invalid input shape. Features must be a 1D or 2D numerical array."
            }), 400

        # Check for NaN or Inf values
        if np.isnan(data_array).any() or np.isinf(data_array).any():
            return jsonify({
                "status": "error",
                "message": "Features contain NaN or infinite values."
            }), 400

    except (ValueError, TypeError) as val_err:
        return jsonify({
            "status": "error",
            "message": f"Invalid numerical values in features: {str(val_err)}"
        }), 400

    # Model inference
    try:
        raw_predictions = model.predict(data_array, verbose=0)
        probabilities = raw_predictions.tolist()
        predicted_classes = [int(np.argmax(prob)) for prob in probabilities]
        predicted_labels = [CLASS_NAMES[idx] if idx < len(CLASS_NAMES) else f"Class {idx}" for idx in predicted_classes]

        # Structure response
        if len(predicted_classes) == 1:
            response_data = {
                "status": "success",
                "prediction": predicted_classes[0],
                "label": predicted_labels[0],
                "confidence": float(np.max(probabilities[0])),
                "probabilities": probabilities[0],
                "class_names": CLASS_NAMES
            }
        else:
            response_data = {
                "status": "success",
                "predictions": predicted_classes,
                "labels": predicted_labels,
                "probabilities": probabilities,
                "class_names": CLASS_NAMES
            }

        return jsonify(response_data), 200

    except Exception as exc:
        logger.error(f"Inference error: {exc}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Internal inference error: {str(exc)}"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
