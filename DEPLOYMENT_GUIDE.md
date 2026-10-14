# Production Deployment & Verification Guide
## Multi-Container Deep Learning Application (Flask REST API + Streamlit UI)

This guide provides end-to-end operational instructions for compiling, deploying, orchestrating, and verifying the multi-container Deep Learning microservice architecture using Docker Compose.

---

### Step 1: Environment Navigation

Open your local terminal (Command Prompt, PowerShell, or bash terminal) and navigate directly to the root directory of the project where `docker-compose.yml` resides:

```bash
cd /path/to/project_root
```

> **Operational Context:**  
> The Docker CLI executes commands relative to the current working directory. Navigating to the directory containing `docker-compose.yml` ensures Docker can automatically locate the service definitions, contextual subdirectories (`./api` and `./ui`), and their respective `Dockerfile` configurations without needing explicit file path flags (`-f`).

---

### Step 2: Image Compilation

Compile the container images for both the backend and frontend microservices using the Compose build engine:

```bash
docker-compose build
```

> **Underlying Docker Mechanics:**  
> 1. **Manifest Parsing:** Docker Compose parses `docker-compose.yml` to identify the build contexts (`./api` and `./ui`) and their respective `Dockerfile` targets.  
> 2. **Base Image Acquisition:** The Docker daemon inspects the local image cache for `python:3.10-slim`. If absent, it queries and pulls the verified minimal Debian-based Python image from Docker Hub.  
> 3. **Layer Caching & Dependency Resolution:** Each `Dockerfile` isolates dependency installation. Docker copies `requirements.txt` independently and runs `pip install --no-cache-dir`, caching this layer so future source code changes do not trigger expensive package re-installations.  
> 4. **Application Code Ingestion:** Docker copies application source files (`app.py`, `model.h5`, configuration files) into the container working directory (`/app`) and commits the final immutable image layers tagged for each service (`flask_dl_api` and `streamlit_dl_ui`).

---

### Step 3: Application Launch

Instantiate and execute the multi-container application in detached mode:

```bash
docker-compose up -d
```

> **Underlying Docker Mechanics:**  
> 1. **Network Provisioning:** Docker automatically provisions an isolated software-defined bridge network named `dl_network`. It configures container-level network interfaces and assigns internal private IP addresses within a virtual subnet.  
> 2. **Embedded DNS Registration:** Docker's embedded DNS server (`127.0.0.11`) registers the container service names. This enables the frontend to route traffic to `http://api:5000/predict` using standard service discovery rather than fragile hard-coded IP addresses.  
> 3. **Service Sequencing:** In accordance with the `depends_on: - api` directive, Docker initiates the `flask_dl_api` backend container first. Once initialized, the `streamlit_dl_ui` frontend container is provisioned.  
> 4. **Detached Execution (`-d` flag):** The `-d` (detached) flag instructs the Docker daemon to fork container processes to the background. This frees your terminal prompt for subsequent administrative tasks rather than locking the session to active stdout/stderr output streams.

---

### Step 4: Container Status Verification

Verify that all orchestrated services are actively running, healthy, and binding their expected network ports:

```bash
docker-compose ps
```

> **Expected Outcome:**  
> The terminal displays an operational table listing both services. Ensure that:
> - `flask_dl_api` displays a state of **`Up`** (or `Up (healthy)`) with port mapping `0.0.0.0:5000->5000/tcp`.  
> - `streamlit_dl_ui` displays a state of **`Up`** with port mapping `0.0.0.0:8501->8501/tcp`.

```text
NAME               IMAGE                     COMMAND                  SERVICE   CREATED         STATUS                   PORTS
flask_dl_api       project_root-api          "python app.py"          api       1 minute ago    Up (healthy)             0.0.0.0:5000->5000/tcp
streamlit_dl_ui    project_root-ui           "streamlit run app.p…"   ui        1 minute ago    Up                       0.0.0.0:8501->8501/tcp
```

---

### Step 5: End-to-End UI Verification

1. Launch your preferred web browser and navigate to the Streamlit frontend interface:
   ```text
   http://localhost:8501
   ```

2. **Conduct the Inference Validation Test:**
   - In the Streamlit dashboard, locate the input sliders or numeric fields (e.g., Feature 1 through Feature 4).
   - Adjust the feature values to test inputs (for example: `75.0`, `80.0`, `28.5`, `45.0`).
   - Click the **Run Prediction** button.

> **Operational Validation Criteria:**  
> When the button is clicked, the Streamlit client dispatches an HTTP POST request across the internal `dl_network` bridge to `http://api:5000/predict`. The Flask backend receives the payload, validates and reshapes the tensor, passes it through the loaded `model.h5` neural network, and returns a JSON response.  
> 
> A successful result is indicated when:
> - The web interface renders the predicted classification category and confidence percentage.
> - The dynamic class probability distribution chart updates on the screen without latency or network timeout warnings.
