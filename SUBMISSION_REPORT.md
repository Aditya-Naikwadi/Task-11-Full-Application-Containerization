# Task 12: Kubernetes Cluster Setup and Deployment
**Candidate Name:** Aditya Naikwadi  
**Course/Track:** Cloud Native Architecture & Container Orchestration  
**Evaluation Platform:** L&T Edutech LMS Platform  
**Cluster Runtime:** Kubernetes v1.37.0 on Minikube (Docker Engine Driver)  

---

## 1. Executive Summary
The primary objective of this project was to architect, provision, and validate an automated Kubernetes deployment pipeline on a local single-node cluster. Moving beyond imperative CLI operations, the solution establishes a declarative continuous-deployment workflow orchestrated via Python (`deploy.py`) and Kubernetes manifests (`apps/v1`). 

The deployed workload achieves high availability through dual active replicas, strict label selector immutability, automated health checking via kubelet liveness and readiness probes, and deterministic external routing configured via a `NodePort` Service abstraction.

---

## 2. Cluster Provisioning & Architecture
The local compute substrate was orchestrated using **Minikube** running on top of **Docker Desktop Engine**:

* **Virtualization & Host Layer:** Docker Desktop (`v29.8.2`) functions as the physical host virtualization substrate, isolating Linux kernel control groups (`cgroups v1/v2`) and namespaces.
* **Control Plane Engine:** Minikube (`v1.39.0`) was initialized with `--driver=docker`, deploying a single privileged container packaging the control plane components (`kube-apiserver`, `etcd`, `kube-controller-manager`, `kube-scheduler`) and worker node components (`kubelet`, `kube-proxy`, and `containerd://2.3.4`).
* **Software-Defined Overlay (CNI):** Initialized the `kindnet` Container Network Interface to allocate internal `PodCIDR` subnets (`10.244.0.0/16`) and generate Netfilter/iptables rules for intra-cluster east-west pod communications.
* **Client & Context Injection:** `kubectl` (`v1.36.1`) was configured via `~/.kube/config`, binding mutual TLS (mTLS) cryptographic keys and cluster endpoints to the local Minikube control plane.

---

## 3. Declarative Infrastructure Specifications

### 3.1 Workload Deployment: `k8s/app-deployment.yaml`
* **API Group & Kind:** `apps/v1` / `Deployment`
* **Replica Redundancy:** Configured with `replicas: 2` to eliminate single points of failure.
* **Update Strategy:** Enforces `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0` to guarantee 100% capacity during revision updates.
* **Selector Integrity:** Enforces exact parity between `.spec.selector.matchLabels` and `.spec.template.metadata.labels` using the standard `app.kubernetes.io/name: web-app` contract.
* **Compute Governance:**
  * `requests`: CPU `100m`, Memory `64Mi` (guaranteed resource floor).
  * `limits`: CPU `250m`, Memory `128Mi` (hard CFS quota ceiling to prevent resource contention).
* **Kubelet Lifecycle Probes:**
  * `readinessProbe`: `HTTP GET /` on port 80 (`initialDelaySeconds: 5`, `periodSeconds: 5`) to gate traffic admission into the service's `EndpointSlice`.
  * `livenessProbe`: `HTTP GET /` on port 80 (`initialDelaySeconds: 10`, `periodSeconds: 10`) to automatically restart deadlocked container processes.

### 3.2 External Network Service: `k8s/app-service.yaml`
* **API Group & Kind:** `v1` / `Service`
* **Service Typology:** `NodePort`
* **Routing Architecture:**
  * Maps virtual internal port (`port: 80`) to the container listener (`targetPort: 80`).
  * Allocates static port `30088` across all host node interfaces.
  * Packets hitting `http://<NodeIP>:30088` are intercepted by the host kernel via Netfilter (`KUBE-NODEPORTS`), dynamically load-balanced via `kube-proxy` rules, and Destination-NAT'd (DNAT) to the active Pod IP (`10.244.0.9` or `10.244.0.10`).

---

## 4. Execution Workflow & Automation Engine
The deployment and diagnostic auditing were automated via the Python controller script [`deploy.py`](deploy.py):

```bash
# 1. Verify cluster status
minikube status

# 2. Execute automated deployment and health audit
python deploy.py
```

### Automation Script Operational Flow (`deploy.py`):
1. **Pre-Flight Validation:** Inspects `minikube status` and `kubectl get nodes` to ensure the node condition evaluates to `Ready: True`.
2. **Server-Side Apply (SSA):** Submits the declarative manifests via `kubectl apply -f k8s/` and triggers reconciliation loops in the `kube-controller-manager`.
3. **Readiness Polling Loop:** Periodically audits the Pod `READY` condition metrics (`1/1`) until steady-state convergence is reached.
4. **Data Plane Validation:** Dispatches queries to verify that `EndpointSlices` are successfully populated with backing Pod IPs.
5. **Ingress Discovery:** Displays external tunnel commands for browser connectivity.

---

## 5. Operational Verification & Visual Evidence

### 5.1 Verification 1: Pod Scheduling and Readiness
**Command Executed:** `kubectl get pods -o wide`  
**SRE Evaluation:** Confirms that all replicas are scheduled to the `minikube` node, assigned individual IP addresses from the PodCIDR block, and report `1/1` Ready with 0 restarts.

**[INSERT SCREENSHOT 1: Terminal output of 'kubectl get pods' showing 'Running' status]**

---

### 5.2 Verification 2: Service Routing & Endpoints
**Command Executed:** `kubectl get svc -o wide && kubectl get endpoints`  
**SRE Evaluation:** Validates that `app-service` exposes port `80:30088/TCP` and that the Endpoints list has registered both active Pod IPs (`10.244.0.9:80`, `10.244.0.10:80`).

**[INSERT SCREENSHOT 2: Terminal output of 'kubectl get services' showing assigned NodePort]**

---

### 5.3 Verification 3: Live Application Ingress in Host Browser
**Access Command:** `minikube service app-service --url` (or `kubectl port-forward svc/app-service 8080:80`)  
**SRE Evaluation:** Demonstrates end-to-end traffic flow from the physical Windows host browser, through the Minikube network bridge, across Netfilter DNAT, and into the Nginx container runtime.

**[INSERT SCREENSHOT 3: Web browser displaying the live application accessed via minikube service]**

---

## 6. Observations & Architectural Benefits
* **Self-Healing & Fault Tolerance:** When an individual Pod container was intentionally terminated (`kubectl delete pod <name>`), the `ReplicaSet` controller detected the delta ($\text{desired} = 2, \text{observed} = 1$) within milliseconds and synthesized a replacement Pod, restoring consensus without service disruption.
* **Decoupled Service Discovery:** By abstracting ephemeral Pod IPs behind a stable `NodePort` virtual interface, upstream clients and external traffic remained unaffected by underlying Pod lifecycle churn and rescheduling.
* **Declarative Idempotency:** Executing `kubectl apply -f k8s` repeatedly maintained system state without recreating running workloads, confirming the stability of Kubernetes declarative reconciliation over imperative scripting.
