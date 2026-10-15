# Task 15: Deep Learning Model Training Pipeline, Evaluation & Production Serialization
## Comprehensive Technical Documentation & MLOps Lifecycle Report

**Candidate Name:** Aditya Naikwadi  
**Course / Track:** Cloud Native DevOps, Container Orchestration & MLOps  
**Evaluation Platform:** L&T Edutech LMS Platform  
**Target Environment:** TensorFlow / Keras 2.x/3.x, Python 3.13, Matplotlib  
**Submission Date:** October 15, 2026  

---

## 1. Executive Summary

This master documentation report fulfills the operational and architectural evaluation criteria for **Task 15: Deep Learning Model Training Pipeline**. Building upon the containerization (Task 11) and Kubernetes orchestration topologies (Tasks 12–14), Task 15 formalizes the core data science and MLOps foundation:

1. **Deterministic Dataset Engineering:** Synthesizing and normalizing a multi-dimensional clinical feature distribution ($N = 2,500$ vectors) partitioned into rigorous Training (70%), Validation (15%), and Holdout Test (15%) splits.
2. **Deep Neural Network (DNN) Classifier Architecture:** Constructing a modular multi-layer perceptron leveraging non-linear activation functions (`ReLU`), Batch Normalization (`BatchNormalization`), and Dropout regularization (`p = 0.2`) to mitigate overfitting.
3. **MLOps Lifecycle & Automated Callbacks:** Incorporating proactive training governors including `ModelCheckpoint` for best-weight persistence, `EarlyStopping` with weight restoration, and dynamic learning rate decay (`ReduceLROnPlateau`).
4. **Generalization Diagnostics & Curve Visualization:** Evaluating out-of-sample holdout test performance and exporting dual-panel diagnostic training curves (`training_performance.png`).
5. **Production Model Serialization:** Exporting the validated model binary directly to `api/model.h5` for seamless live inference serving by the Flask backend microservice and Streamlit UI dashboard.

---

## 2. Deep Learning Pipeline Architecture (`train.py`)

The end-to-end training pipeline is encapsulated in [`train.py`](./train.py) and executes across six distinct lifecycle phases:

```
+-----------------------------------------------------------------------------------------+
|                                    TASK 15 PIPELINE                                      |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|  [Clinical Feature Vectors] ---> [Normalization] ---> [70/15/15 Data Split]             |
|                                                              |                          |
|                                                              v                          |
|                                                  [DNN Architecture: 64->32->16->3]      |
|                                                              |                          |
|                                                              v                          |
|  [Adam Optimizer (lr=0.005)] <----------------- [MLOps Automated Callbacks]             |
|                                                  - ModelCheckpoint (api/model.h5)       |
|                                                  - EarlyStopping (patience=6)           |
|                                                  - ReduceLROnPlateau (factor=0.5)       |
|                                                              |                          |
|                                                              v                          |
|                                                  [Holdout Evaluation (Test Set)]        |
|                                                              |                          |
|                                                              v                          |
|                                                  [Visualization & Serialization]        |
|                                                  - training_performance.png (Plots)     |
|                                                  - api/model.h5 (Trained Weights)       |
|                                                              |                          |
|                                                              v                          |
|                                                  [Flask API & Streamlit Serving]        |
+-----------------------------------------------------------------------------------------+
```

---

### 2.1 Dataset Generation & Feature Schema

The dataset generates $2,500$ observations mapped across four fundamental patient clinical features aligned with the production input schema:

* **Feature 1 (Glucose):** Gaussian distribution ($\mu = 100, \sigma = 25$, range $\sim 70 - 200 \text{ mg/dL}$).
* **Feature 2 (Blood Pressure):** Gaussian distribution ($\mu = 80, \sigma = 15$, range $\sim 60 - 140 \text{ mmHg}$).
* **Feature 3 (BMI):** Gaussian distribution ($\mu = 27, \sigma = 6$, range $\sim 18 - 45 \text{ kg/m}^2$).
* **Feature 4 (Age):** Gaussian distribution ($\mu = 45, \sigma = 15$, range $\sim 18 - 80 \text{ years}$).

#### Multi-Class Label Assignment
Target labels $y \in \{0, 1, 2\}$ are categorized according to compound clinical risk scoring:
$$\text{Risk Score} = 0.4(F_1 - 70) + 0.3(F_2 - 60) + 1.5(F_3 - 18) + 0.5(F_4 - 18)$$
* **Class 0 (Low Risk):** $\text{Risk Score} \le 60$
* **Class 1 (Moderate Risk):** $60 < \text{Risk Score} \le 95$
* **Class 2 (High Risk):** $\text{Risk Score} > 95$

#### Standard Normalization & Splitting
Input vectors are normalized via Z-score standardization ($Z = \frac{X - \mu}{\sigma + \epsilon}$) to eliminate gradient distortion across differently scaled features. The dataset is deterministically divided using a fixed random seed (`SEED = 42`):
* **Training Set:** $1,750$ samples ($70\%$)
* **Validation Set:** $375$ samples ($15\%$)
* **Holdout Test Set:** $375$ samples ($15\%$)

---

### 2.2 Neural Network Architecture Design

The model is built using the Keras Sequential API with intentional regularization layers to ensure strong generalization:

| Layer # | Layer Type | Output Shape | Parameters | Activation | Regularization / Purpose |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **0** | `Input` | `(None, 4)` | $0$ | — | Ingests 4 normalized clinical features |
| **1** | `Dense` | `(None, 64)` | $320$ | `ReLU` | High-capacity initial feature projection |
| **2** | `BatchNormalization` | `(None, 64)` | $256$ | — | Stabilizes hidden layer distribution & accelerates convergence |
| **3** | `Dropout (0.2)` | `(None, 64)` | $0$ | — | Randomly zeroes 20% of activations to suppress co-adaptation |
| **4** | `Dense` | `(None, 32)` | $2,080$ | `ReLU` | Intermediate feature synthesis |
| **5** | `BatchNormalization` | `(None, 32)` | $128$ | — | Normalizes hidden representation |
| **6** | `Dropout (0.2)` | `(None, 32)` | $0$ | — | Regularization |
| **7** | `Dense` | `(None, 16)` | $528$ | `ReLU` | Low-dimensional abstraction bottleneck |
| **8** | `BatchNormalization` | `(None, 16)` | $64$ | — | Final hidden layer normalization |
| **9** | `Dense` (Output) | `(None, 3)` | $51$ | `Softmax` | Generates calibrated probabilities across all 3 risk classes |

* **Loss Function:** `sparse_categorical_crossentropy` (exact mathematical alignment for non-one-hot integer target classes).
* **Optimization Algorithm:** `Adam` with an initial learning rate $\alpha = 0.005$.

---

### 2.3 MLOps Callbacks & Training Governance

To avoid manual over-training or sub-optimal weight selection, three automated Keras callbacks govern training:

1. **`ModelCheckpoint`:**
   * **Monitored Metric:** `val_accuracy` (`mode="max"`)
   * **Behavior:** Saves the model binary directly to `api/model.h5` exclusively when validation accuracy surpasses previous epoch records (`save_best_only=True`).
2. **`EarlyStopping`:**
   * **Monitored Metric:** `val_loss`
   * **Patience:** 6 epochs
   * **Behavior:** Terminates training if validation loss ceases to decrease for 6 consecutive epochs and restores weights from the absolute best epoch (`restore_best_weights=True`).
3. **`ReduceLROnPlateau`:**
   * **Monitored Metric:** `val_loss`
   * **Decay Factor:** $0.5$ (halves learning rate)
   * **Patience:** 3 epochs
   * **Minimum LR:** $1 \times 10^{-5}$

---

## 3. Execution Commands & Artifact Verification

### 3.1 Running the Training Script
From the project root directory:

```powershell
# Navigate to workspace
cd "c:\Users\naikw\OneDrive\Desktop\project\Task 11"

# Execute training pipeline
python train.py
```

### 3.2 Output Verification & Saved Artifacts

Upon completion of `python train.py`, the following deliverables are automatically synthesized:

1. **`api/model.h5`:** The serialized HDF5 model artifact containing complete network topology, layer weights, and optimizer configuration.
2. **`training_performance.png`:** High-resolution (300 DPI) dual-panel diagnostic visualization showing accuracy and loss trajectories across all trained epochs.

```powershell
# Verify generated artifact sizes and timestamps
Get-Item "api\model.h5", "training_performance.png" | Format-Table Name, Length, LastWriteTime
```

---

## 4. Evidence Collection & Visual Artifacts

### 4.1 Artifact 1: Training Execution in Terminal
**Description:** Terminal output capturing data synthesis, dataset partitioning, Keras model summary, epoch-by-epoch loss/accuracy metrics, callback triggers, and final holdout test evaluation scores.

**[INSERT SCREENSHOT 1: Terminal output of 'python train.py' showing training progress and final metrics]**

---

### 4.2 Artifact 2: Training Performance Diagnostics (`training_performance.png`)
**Description:** Visual inspection of `training_performance.png` demonstrating training vs. validation accuracy convergence (left panel) and categorical cross-entropy loss decay with the horizontal holdout test baseline (right panel).

**[INSERT SCREENSHOT 2: Dual-panel plot of training and validation accuracy and loss curves]**

---

### 4.3 Artifact 3: Model Serialization & File System Verification
**Description:** File listing in terminal or IDE file explorer confirming the presence of `api/model.h5` and `training_performance.png` with valid file sizes.

**[INSERT SCREENSHOT 3: Directory listing proving 'api/model.h5' and 'training_performance.png' existence]**

---

### 4.4 Artifact 4: Live Serving Integration via Streamlit UI
**Description:** Web browser screenshot of the Streamlit dashboard (`http://localhost:8501`) connected to the backend (`🟢 API Service Connected`), demonstrating live feature vector input and real-time inference computed by the newly trained model.

**[INSERT SCREENSHOT 4: Streamlit web UI demonstrating live inference using the trained model]**

---

## 5. End-to-End Microservice Integration

The serialized model is immediately consumable across the full application stack without code modifications:

1. **Flask API (`api/app.py`):**
   * Automatically executes `tf.keras.models.load_model('api/model.h5')` upon initialization.
   * Serves inference payloads via HTTP POST at `/predict`.
   * Provides health status at `/health` and service discovery at `/`.
2. **Streamlit Frontend (`ui/app.py`):**
   * Dispatches feature vectors to `http://127.0.0.1:5000/predict`.
   * Renders predicted risk categories (`Class 0`, `Class 1`, `Class 2`), confidence levels, and interactive probability distribution bar charts.

---

## 6. LMS Final Submission Checklist

- [x] **Pipeline Script Created:** Completed and verified [`train.py`](./train.py) with data synthesis, DNN architecture, and callbacks.
- [x] **Model Successfully Trained:** Executed pipeline achieving high test accuracy with categorical cross-entropy optimization.
- [x] **Model Artifact Serialized:** Model weights and architecture stored in [`api/model.h5`](./api/model.h5).
- [x] **Performance Plot Generated:** Created dual-curve diagnostic plot saved to [`training_performance.png`](./training_performance.png).
- [x] **Backend & Frontend Integration:** Verified that `api/app.py` loads `model.h5` and serves live inference to `ui/app.py`.
- [x] **Evidence Placeholders Configured:** All 4 visual screenshot placeholders clearly structured and bolded for LMS evaluator grading.
