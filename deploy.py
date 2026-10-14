#!/usr/bin/env python3
"""
Kubernetes Cluster Deployment & Operational Verification Engine
Task 12: Kubernetes Cluster Setup and Deployment
Author: Senior DevOps Engineer & SRE

This script automates:
1. Environment pre-flight checks (Minikube / Docker / kubectl liveness).
2. Declarative manifest ingestion (kubectl apply -f k8s/).
3. Real-time control plane reconciliation polling & readiness auditing.
4. Data plane service endpoint validation.
"""

import sys
import time
import subprocess
from typing import Tuple, List


def run_command(cmd: List[str], check: bool = True, capture: bool = True) -> Tuple[int, str]:
    """Execute a system command safely via subprocess and capture stdout/stderr."""
    command_str = " ".join(cmd)
    print(f"\n[EXEC] ==> {command_str}")
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.STDOUT if capture else None,
            text=True,
            check=False,
            shell=False
        )
        output = result.stdout.strip() if result.stdout else ""
        if result.returncode != 0 and check:
            print(f"[ERROR] Command exited with code {result.returncode}:\n{output}", file=sys.stderr)
            sys.exit(result.returncode)
        return result.returncode, output
    except FileNotFoundError:
        print(f"[FATAL] Required binary not found in PATH: {cmd[0]}", file=sys.stderr)
        sys.exit(1)


def verify_cluster_runtime():
    """Verify that Minikube is running and kubectl is targeting the active context."""
    print("=" * 70)
    print("PHASE 1: PRE-FLIGHT ENVIRONMENT & CLUSTER STATE VALIDATION")
    print("=" * 70)

    # 1. Check Minikube Status
    code, output = run_command(["minikube", "status"], check=False)
    if code != 0 or "Running" not in output:
        print("[WARN] Minikube is not reporting steady-state 'Running'. Attempting initialization...")
        run_command(["minikube", "start", "--driver=docker"], check=True)
    else:
        print("[OK] Minikube cluster is healthy and operational.")
        print(output)

    # 2. Check Node Readiness via kubectl
    code, output = run_command(["kubectl", "get", "nodes", "-o", "wide"])
    print("\n[CLUSTER NODES]:")
    print(output)

    if "Ready" not in output:
        print("[FATAL] Cluster node is not in 'Ready' state. Check CNI status.", file=sys.stderr)
        sys.exit(1)


def apply_declarative_manifests(manifest_dir: str = "k8s"):
    """Declaratively submit all Kubernetes manifests to the API Server."""
    print("\n" + "=" * 70)
    print("PHASE 2: DECLARATIVE MANIFEST INGESTION (SERVER-SIDE RECONCILIATION)")
    print("=" * 70)

    code, output = run_command(["kubectl", "apply", "-f", manifest_dir])
    print(output)


def monitor_rollout_and_readiness(timeout_sec: int = 60):
    """Poll pod states and probe conditions until all replicas report 1/1 Ready."""
    print("\n" + "=" * 70)
    print("PHASE 3: OPERATIONAL RECONCILIATION & READINESS PROBE AUDIT")
    print("=" * 70)
    print(f"Polling pod conditions for up to {timeout_sec} seconds...")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        code, output = run_command(["kubectl", "get", "pods", "-o", "wide"], check=False)
        print("\n--- Live Pod State ---")
        print(output)

        lines = output.splitlines()
        pod_rows = [line for line in lines if not line.startswith("NAME") and line.strip()]

        # Verify that all pods are Running and all containers are Ready (e.g., 1/1)
        all_ready = True
        for row in pod_rows:
            parts = row.split()
            if len(parts) >= 3:
                ready_metric = parts[1]
                status = parts[2]
                ready_current, ready_expected = map(int, ready_metric.split("/"))
                if status != "Running" or ready_current != ready_expected:
                    all_ready = False
                    break

        if pod_rows and all_ready:
            print(f"\n[SUCCESS] All {len(pod_rows)} Pod replicas converged to 'Running' with full Readiness!")
            return

        time.sleep(5)

    print("\n[WARN] Timeout reached before all pods reported Ready. Inspecting event log:")
    run_command(["kubectl", "get", "events", "--sort-by=.metadata.creationTimestamp"], check=False)


def audit_services_and_endpoints():
    """Verify service routing, allocated NodePorts, and EndpointSlice registrations."""
    print("\n" + "=" * 70)
    print("PHASE 4: SERVICE DISCOVERY & DATA PLANE ROUTING VALIDATION")
    print("=" * 70)

    # Inspect Services
    code, svc_output = run_command(["kubectl", "get", "services", "-o", "wide"])
    print("\n[KUBERNETES SERVICES]:")
    print(svc_output)

    # Inspect Endpoints
    code, ep_output = run_command(["kubectl", "get", "endpoints", "-o", "wide"], check=False)
    print("\n[BACKING POD ENDPOINTS]:")
    print(ep_output)


def print_access_instructions():
    """Output commands to bridge the external host browser to the running workload."""
    print("\n" + "=" * 70)
    print("PHASE 5: INGRESS & EXTERNAL ACCESS")
    print("=" * 70)
    print("To open the live application in your browser, execute:")
    print("  >> minikube service app-service --url")
    print("\nAlternatively, forward the service directly to localhost:")
    print("  >> kubectl port-forward svc/app-service 8080:80")
    print("  Then browse to: http://localhost:8080")
    print("=" * 70)


def main():
    try:
        verify_cluster_runtime()
        apply_declarative_manifests("k8s")
        monitor_rollout_and_readiness(timeout_sec=90)
        audit_services_and_endpoints()
        print_access_instructions()
    except KeyboardInterrupt:
        print("\n[ABORTED] Deployment script interrupted by user.")
        sys.exit(130)


if __name__ == "__main__":
    main()
