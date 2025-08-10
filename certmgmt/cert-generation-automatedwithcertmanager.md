# Automated Certificate Generation: cert-manager on AKS with ACME Protocol

This guide demonstrates **fully automated certificate generation** using **cert-manager** on Azure Kubernetes Service (AKS) with the **ACME protocol**, **Let's Encrypt**, and **NGINX Ingress Controller**. This approach uses **HTTP-01 challenges** for completely automated certificate issuance without manual DNS record creation. This builds upon the concepts from [cert-basics.md](./cert-basics.md), [cert-generation-basics.md](./cert-generation-basics.md), and [cert-generation-semiautomated.md](./cert-generation-semiautomated.md).

## Architecture Overview: Automated ACME Process with cert-manager and NGINX Ingress

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    CERT-MANAGER HTTP-01 FLOW WITH NGINX INGRESS ON AKS                            │
│                                                                                                     │
│  🌐 AZURE DNS              🏗️ AKS CLUSTER                     🏛️ LET'S ENCRYPT CA                  │
│     (A Record Only)         (Kubernetes Automation)             (ACME-Compatible CA)              │
│                                                                                                     │
│  ┌─────────────────┐      ┌─────────────────────────────────┐      ┌─────────────────┐             │
│  │ DNS A Record    │      │ 🌉 NGINX Ingress Controller    │      │ 4. HTTP-01      │             │
│  │                 │      │    IP: 128.85.229.216          │      │    Challenge    │             │
│  │ certmanagerdemo │ ◄────┤ ┌─────────────────────────────┐ │      │    Validation   │             │
│  │ .srinman.com    │      │ │ 1. Ingress with TLS Config  │ │      │                 │             │
│  │ → 128.85.229.216│      │ │    cert-manager annotations │ │      │ 🔍 HTTP GET     │             │
│  │                 │      │ └─────────────────────────────┘ │      │ /.well-known/   │             │
│  │ (ONE-TIME SETUP)│      │                                 │      │ acme-challenge/ │             │
│  └─────────────────┘      │ ┌─────────────────────────────┐ │      │ <token>         │             │
│                            │ │ 2. ClusterIssuer HTTP-01    │ │      └─────────────────┘             │
│                            │ │    (Let's Encrypt + nginx)  │ │               │                       │
│                            │ └─────────────────────────────┘ │               │ 5. Issue              │
│                            │                                 │               ▼    Certificate       │
│                            │ ┌─────────────────────────────┐ │      ┌─────────────────┐             │
│                            │ │ 3. Certificate Auto-Created │ │      │ 📜 Signed Cert  │             │
│                            │ │    from Ingress TLS         │ │      │ � Cert Chain   │             │
│                            │ └─────────────────────────────┘ │      │ � 90-day Valid │             │
│                            │                                 │      │ � Auto-Renewal │             │
│                            │ ┌─────────────────────────────┐ │      └─────────────────┘             │
│                            │ │ 6. TLS Secret Auto-Created  │ │               │                       │
│                            │ │    certmanagerdemo-tls...   │ │               │ 7. Store as           │
│                            │ └─────────────────────────────┘ │               ▼    Kubernetes Secret  │
│                            │                 │               │      ┌─────────────────┐             │
│                            │                 ▼               │      │ 🔐 TLS Secret   │             │
│                            │ ┌─────────────────────────────┐ │      │ • tls.crt       │             │
│                            │ │ 8. NGINX TLS Termination    │ │      │ • tls.key       │             │
│                            │ │    (Ingress Controller)     │ │      │ • ca.crt        │             │
│                            │ └─────────────────────────────┘ │      └─────────────────┘             │
│                            │                 │               │                                        │
│                            │                 ▼               │                                        │
│                            │ ┌─────────────────────────────┐ │                                        │
│                            │ │ 9. Echoserver Application   │ │                                        │
│                            │ │    (HTTP only - port 8080)  │ │                                        │
│                            │ └─────────────────────────────┘ │                                        │
│                            └─────────────────────────────────┘                                        │
│                                             │                                                          │
│                                             ▼                                                          │
│                                    ┌─────────────────┐                                                │
│                                    │ 🌐 BROWSER      │                                                │
│                                    │   (Relying      │                                                │
│                                    │    Party)       │                                                │
│                                    │                 │                                                │
│                                    │ ✅ Validates    │                                                │
│                                    │    Let's Encrypt│                                                │
│                                    │    Certificate  │                                                │
│                                    │ 🔒 Trusted      │                                                │
│                                    │    HTTPS via    │                                                │
│                                    │    NGINX        │                                                │
│                                    └─────────────────┘                                                │
│                                                                                                     │
│  💡 Key Innovation: Fully automated HTTP-01 challenges with NO manual DNS TXT records required    │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Understanding cert-manager

### **What is cert-manager?**

**cert-manager** is a **Kubernetes-native certificate management controller** that automates the issuance and management of TLS certificates from various sources, including Let's Encrypt via the ACME protocol.

### **cert-manager Components:**

```
┌─────────────────────────────────────────────────────────────┐
│                   CERT-MANAGER ARCHITECTURE                 │
│                                                             │
│  🎛️ CUSTOM RESOURCES        🤖 CONTROLLERS       📦 OUTPUTS │
│     (Declarative Config)       (Automation Logic)   (K8s)   │
│                                                             │
│  Certificate                 cert-manager           Secret  │
│  ├── Domain names           Controller               ├── tls.crt │
│  ├── Issuer reference       ├── Watches CRs         ├── tls.key │
│  └── Secret name            ├── ACME client         └── ca.crt  │
│                             ├── DNS-01 solver                │
│  ClusterIssuer              └── Secret manager              │
│  ├── ACME server URL                                        │
│  ├── Email contact          Challenge                       │
│  ├── Private key ref        ├── DNS record name             │
│  └── DNS-01 config          ├── Token value                 │
│                             └── Validation status           │
│  CertificateRequest                                         │
│  ├── CSR (generated)        Order                          │
│  ├── Issuer reference       ├── Certificate request        │
│  └── Status tracking        ├── Challenge list             │
│                             └── Fulfillment status         │
│                                                             │
│  DECLARATIVE:               REACTIVE:               STATE:   │
│  ✅ What you want          ✅ How to achieve it    ✅ Result │
│  ❌ How to do it           ❌ Manual steps         ❌ Process│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **How cert-manager Differs from certbot:**

| Aspect | certbot (Semi-Automated) | cert-manager (Fully Automated) |
|--------|--------------------------|--------------------------------|
| **Platform** | Linux command-line tool | Kubernetes-native controller |
| **Configuration** | Command-line parameters | Declarative YAML manifests |
| **Challenge Method** | Manual TXT record creation | ✅ Automated HTTP-01 challenges |
| **DNS Requirements** | TXT record management | ✅ Simple A record (one-time setup) |
| **Certificate Storage** | File system (/etc/letsencrypt/) | ✅ Kubernetes Secrets |
| **Renewal** | Cron jobs or systemd timers | ✅ Kubernetes controller loop |
| **Integration** | Manual web server config | ✅ Automatic Ingress integration |
| **Scalability** | Single server | ✅ Cluster-wide, multi-certificate |
| **State Management** | File-based | ✅ Kubernetes API-driven |

## Prerequisites

### **AKS Cluster Requirements**

**🚨 IMPORTANT**: This demo requires a working AKS cluster with **LoadBalancer support** for NGINX Ingress Controller.

### **Network Security Group (NSG) Configuration**

**🔥 CRITICAL**: Ensure your AKS cluster's Network Security Group allows HTTP/HTTPS traffic from Let's Encrypt validation servers for HTTP-01 challenge validation.

#### **Required Firewall Rules for Let's Encrypt HTTP-01 Challenges**

According to [Let's Encrypt's Integration Guide](https://letsencrypt.org/docs/integration-guide/#firewall-configuration), the following firewall configuration is required:

```bash
# Required inbound traffic for HTTP-01 ACME challenge:
# - Port 80 (HTTP) must be open from Internet
# - Let's Encrypt does not publish IP ranges for validation servers
# - Validation IPs will change without notice

# Your NSG must allow:
# 1. Inbound port 80 traffic from 0.0.0.0/0 (Internet)
# 2. Inbound port 443 traffic from 0.0.0.0/0 (Internet) 
#    [for normal HTTPS traffic]

# Additional requirements:
# - Outbound port 443 traffic (for ACME client communication)
# - Port 53 traffic (TCP and UDP) to authoritative DNS servers
```

#### **Azure NSG Rules for HTTP-01 Validation**

```bash
# Example Azure NSG rules for Let's Encrypt HTTP-01 validation:

# Rule 1: Allow HTTP traffic for ACME challenges
az network nsg rule create \
  --resource-group <your-resource-group> \
  --nsg-name <your-nsg-name> \
  --name AllowHTTPForACME \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes Internet \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 80 \
  --description "Allow HTTP traffic for Let's Encrypt ACME HTTP-01 challenges"

# Rule 2: Allow HTTPS traffic for normal operation
az network nsg rule create \
  --resource-group <your-resource-group> \
  --nsg-name <your-nsg-name> \
  --name AllowHTTPS \
  --priority 110 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes Internet \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 443 \
  --description "Allow HTTPS traffic for secure connections"
```

#### **Why These Rules Are Required**

```
┌─────────────────────────────────────────────────────────────┐
│           LET'S ENCRYPT HTTP-01 VALIDATION FLOW             │
│                                                             │
│  🌍 Let's Encrypt Validation Servers                       │
│  (Unpublished IP ranges, change without notice)            │
│                    │                                        │
│                    ▼ HTTP GET Request                       │
│  🔥 Your NSG/Firewall (MUST ALLOW)                         │
│  • Port 80 from Internet (0.0.0.0/0)                      │
│  • Cannot restrict to specific IPs                         │
│                    │                                        │
│                    ▼                                        │
│  🌉 NGINX Ingress Controller                               │
│  • IP: 128.85.229.216                                      │
│  • Routes /.well-known/acme-challenge/* to cert-manager    │
│                    │                                        │
│                    ▼                                        │
│  🤖 cert-manager Challenge Response                        │
│  • Serves challenge token at HTTP endpoint                 │
│  • Validation succeeds → Certificate issued                │
│                                                             │
│  💡 Security Note: HTTP access is required for validation, │
│  but Let's Encrypt recommends redirecting HTTP → HTTPS     │
│  for normal traffic (after challenge completion)           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **Important Security Considerations**

⚠️ **Common Mistake**: Restricting HTTP traffic to specific IP addresses will break HTTP-01 validation because:
- Let's Encrypt does not publish their validation server IP ranges
- Validation IPs change frequently without notice
- Attempting to allowlist specific IPs will cause certificate issuance failures

✅ **Best Practice**: As recommended by Let's Encrypt:
- Allow HTTP (port 80) access from Internet for ACME validation
- Configure automatic HTTP → HTTPS redirects for normal traffic
- This provides same security level while enabling certificate automation

🔒 **Note**: This configuration is only required during certificate issuance and renewal. The validation traffic is minimal and only accesses the specific `/.well-known/acme-challenge/` path.

### **Required Tools**

```bash
# Install kubectl (if not already installed)
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (for cert-manager installation)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installations
kubectl version --client
helm version
```

### **Domain Setup**

For this demonstration, we'll use `certmanagerdemo.srinman.com` hosted on Azure Public DNS:

```bash
# Set domain variable for easier reuse
export DOMAIN="certmanagerdemo.srinman.com"
export EMAIL="snmanivel@gmail.com"

echo "Working with domain: $DOMAIN"
echo "Contact email: $EMAIL"
```

## Mapping PKI Entities to cert-manager Model

Building on our foundational concepts from [cert-basics.md](./cert-basics.md):

### **Entity/Subject (Certificate Holder)**
```
┌─────────────────────────────────────────────────────────────┐
│                ENTITY/SUBJECT IN CERT-MANAGER               │
│                                                             │
│  🏗️ AKS CLUSTER & APPLICATIONS                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Role: Certificate Consumer                          │   │
│  │                                                     │   │
│  │ Components:                                         │   │
│  │ ✅ Echoserver Application (Direct TLS termination) │   │
│  │ ✅ LoadBalancer service (public IP exposure)       │   │
│  │                                                     │   │
│  │ What's Automated:                                   │   │
│  │ • Certificate provisioning via cert-manager        │   │
│  │ • Automatic renewal before expiration              │   │
│  │ • Secret creation and mounting                     │   │
│  │ • Ingress TLS configuration                        │   │
│  │                                                     │   │
│  │ What Requires Manual Action:                       │   │
│  │ • DNS TXT record creation (DNS-01 challenge)       │   │
│  │ • DNS A record for LoadBalancer IP                 │   │
│  │ • Initial cert-manager configuration               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Certificate Authority (CA)**
```
┌─────────────────────────────────────────────────────────────┐
│           CERTIFICATE AUTHORITY IN CERT-MANAGER             │
│                                                             │
│  🏛️ LET'S ENCRYPT (via ClusterIssuer)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Role: ACME Server Integration                       │   │
│  │                                                     │   │
│  │ cert-manager Integration:                           │   │
│  │ ✅ ACME client embedded in controller              │   │
│  │ ✅ Automatic account registration                  │   │
│  │ ✅ Challenge orchestration                         │   │
│  │ ✅ Certificate retrieval and parsing               │   │
│  │ ✅ Renewal monitoring and automation               │   │
│  │                                                     │   │
│  │ ClusterIssuer Configuration:                       │   │
│  │ • ACME server URL (Let's Encrypt)                  │   │
│  │ • Contact email for account                        │   │
│  │ • Private key storage (Kubernetes Secret)         │   │
│  │ • DNS-01 solver configuration                      │   │
│  │                                                     │   │
│  │ Benefits over Direct ACME:                         │   │
│  │ ✅ Kubernetes-native resource management           │   │
│  │ ✅ Multi-certificate coordination                  │   │
│  │ ✅ Automatic renewal orchestration                 │   │
│  │ ✅ Event-driven certificate lifecycle             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Relying Party (Client)**
```
┌─────────────────────────────────────────────────────────────┐
│              RELYING PARTY IN CERT-MANAGER                  │
│                                                             │
│  🌐 EXTERNAL CLIENTS (UNCHANGED FROM PREVIOUS GUIDES)       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Role: Certificate Validator                         │   │
│  │                                                     │   │
│  │ Client Perspective:                                 │   │
│  │ • Connects to: https://certmanagerdemo.srinman.com │   │
│  │ • Resolves DNS to: LoadBalancer public IP          │   │
│  │ • Receives certificate from: Echoserver Application │   │
│  │ • Validates against: Let's Encrypt trust chain     │   │
│  │                                                     │   │
│  │ Certificate Validation (Same Process):              │   │
│  │ ✅ Check certificate chain                          │   │
│  │ ✅ Verify Let's Encrypt signature                   │   │
│  │ ✅ Validate certificate dates                       │   │
│  │ ✅ Confirm hostname match                           │   │
│  │ ✅ Check revocation status (OCSP)                   │   │
│  │                                                     │   │
│  │ Key Advantage:                                      │   │
│  │ ✅ Transparent to clients (same HTTPS experience)  │   │
│  │ ✅ Automatic certificate updates                    │   │
│  │ ✅ High availability through Kubernetes            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Install cert-manager

### **Install cert-manager using Helm**

```bash
# Add the Jetstack Helm repository
helm repo add jetstack https://charts.jetstack.io

# Update your local Helm chart repository cache
helm repo update

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
    --namespace cert-manager \
    --create-namespace \
    --version v1.13.3 \
    --set installCRDs=true \
    --set global.leaderElection.namespace=cert-manager

# Verify installation
kubectl get pods --namespace cert-manager

# Expected output:
# NAME                                      READY   STATUS    RESTARTS   AGE
# cert-manager-866bd4b8-xxxxx              1/1     Running   0          1m
# cert-manager-cainjector-6d7b98ff-xxxxx   1/1     Running   0          1m
# cert-manager-webhook-8df6c974-xxxxx      1/1     Running   0          1m
```

### **Verify cert-manager CRDs**

```bash
# Check Custom Resource Definitions
kubectl get crd | grep cert-manager

# Expected CRDs:
# certificaterequests.cert-manager.io
# certificates.cert-manager.io  
# challenges.acme.cert-manager.io
# clusterissuers.cert-manager.io
# issuers.cert-manager.io
# orders.acme.cert-manager.io
```

### **Understanding cert-manager Components**

```
┌─────────────────────────────────────────────────────────────┐
│               CERT-MANAGER COMPONENT ROLES                  │
│                                                             │
│  🎛️ cert-manager Controller:                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Watches Certificate resources                     │   │
│  │ • Creates CertificateRequests                       │   │
│  │ • Manages certificate lifecycle                     │   │
│  │ • Updates Kubernetes Secrets                        │   │
│  │ • Handles certificate renewal                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🌐 cert-manager Webhook:                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Validates Certificate configurations              │   │
│  │ • Provides admission control                        │   │
│  │ • Ensures resource consistency                      │   │
│  │ • Prevents invalid configurations                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💉 cert-manager CA Injector:                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Injects CA certificates into webhooks             │   │
│  │ • Manages cert-manager's own certificates           │   │
│  │ • Ensures secure communication within cluster       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 2: Install NGINX Ingress Controller

### **Install NGINX Ingress Controller**

```bash
# Add the ingress-nginx repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install the NGINX ingress controller
helm install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx \
    --create-namespace \
    --set controller.service.type=LoadBalancer \
    --set controller.service.externalTrafficPolicy=Local

# Wait for the ingress controller to get an external IP
echo "Waiting for NGINX Ingress Controller to get external IP..."
kubectl wait --namespace ingress-nginx \
    --for=condition=ready pod \
    --selector=app.kubernetes.io/component=controller \
    --timeout=120s

# Get the external IP address
INGRESS_IP=$(kubectl get service ingress-nginx-controller \
    --namespace ingress-nginx \
    --output jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "NGINX Ingress External IP: $INGRESS_IP"
export INGRESS_IP
```

## Step 3: Configure ClusterIssuer for Let's Encrypt

### **Create ClusterIssuer Resource**

```bash
# Create ClusterIssuer for Let's Encrypt with HTTP-01 challenge
cat << EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-http01
spec:
  acme:
    # Let's Encrypt production server
    server: https://acme-v02.api.letsencrypt.org/directory
    
    # Email address for ACME account registration
    email: $EMAIL
    
    # Secret to store the ACME account private key
    privateKeySecretRef:
      name: letsencrypt-http01-private-key
    
    # HTTP-01 challenge configuration
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

**✅ Benefits of HTTP-01 with NGINX Ingress**: This configuration uses **HTTP-01 challenges** with the NGINX ingress controller, providing fully automated certificate issuance without manual DNS record creation.

### **Verify ClusterIssuer Status**

```bash
# Check ClusterIssuer status
kubectl describe clusterissuer letsencrypt-http01

# Look for status conditions:
# Status:
#   Acme:
#     Last Registered Email:  snmanivel@gmail.com
#     Uri:                   https://acme-v02.api.letsencrypt.org/acme/acct/...
#   Conditions:
#     Last Transition Time:  2025-08-09T...
#     Message:              The ACME account was registered with the ACME server
#     Observed Generation:   1
#     Reason:               ACMEAccountRegistered
#     Status:               True
#     Type:                 Ready
```

### **Understanding ClusterIssuer vs Issuer**

```
┌─────────────────────────────────────────────────────────────┐
│              CLUSTERISSUER VS ISSUER SCOPING                │
│                                                             │
│  🌐 ClusterIssuer (Cluster-wide):                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Available to all namespaces                       │   │
│  │ • Single ACME account for entire cluster            │   │
│  │ • Shared rate limits across all certificates        │   │
│  │ • Centralized certificate authority configuration   │   │
│  │ • Ideal for: Multi-tenant clusters, shared CA       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🏠 Issuer (Namespace-scoped):                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Available only within specific namespace          │   │
│  │ • Separate ACME accounts per namespace              │   │
│  │ • Isolated rate limits per namespace                │   │
│  │ • Namespace-specific CA configurations              │   │
│  │ • Ideal for: Multi-tenant isolation, team boundaries│   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Best Practice: Use ClusterIssuer for shared CAs        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 4: Deploy Echoserver Application with Ingress

### **Create Echoserver Application**

```bash
# Create namespace for our demo
kubectl create namespace certmanager-demo

# Deploy echoserver application
cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: echoserver
  namespace: certmanager-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: echoserver
  template:
    metadata:
      labels:
        app: echoserver
    spec:
      containers:
      - name: echoserver
        image: k8s.gcr.io/echoserver:1.4
        ports:
        - containerPort: 8080
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
---
apiVersion: v1
kind: Service
metadata:
  name: echoserver-service
  namespace: certmanager-demo
spec:
  type: ClusterIP
  selector:
    app: echoserver
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: echoserver-ingress
  namespace: certmanager-demo
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-http01
spec:
  tls:
  - hosts:
    - $DOMAIN
    secretName: certmanagerdemo-tls-secret
  rules:
  - host: $DOMAIN
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: echoserver-service
            port:
              number: 80
EOF
```

### **Verify Application and Ingress Deployment**

```bash
# Wait for echoserver pods to be ready
echo "Waiting for echoserver deployment..."
kubectl wait --for=condition=ready pod \
  --selector=app=echoserver \
  --namespace=certmanager-demo \
  --timeout=120s

# Verify ingress creation
kubectl get ingress --namespace certmanager-demo

# Expected output:
# NAME                CLASS    HOSTS                          ADDRESS          PORTS     AGE
# echoserver-ingress  <none>   certmanagerdemo.srinman.com    128.85.229.216   80, 443   1m

# Get the NGINX Ingress Controller IP (should match ingress ADDRESS)
echo "NGINX Ingress Controller IP:"
kubectl get service ingress-nginx-controller \
    --namespace ingress-nginx \
    --output jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo
```

### **Understanding the NGINX Ingress Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                NGINX INGRESS TLS ARCHITECTURE                │
│                                                             │
│  🌐 Internet Traffic:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Browser → DNS → LoadBalancer IP → AKS Service       │   │
│  │ https://certmanagerdemo.srinman.com:443             │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  ⚖️ AKS LoadBalancer Service:                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Type: LoadBalancer                                  │   │
│  │ External IP: $LOADBALANCER_IP                       │   │
│  │ Port 80 → Pod 8080 (HTTP)                          │   │
│  │ Port 443 → Pod 8443 (HTTPS/TLS)                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  � Echoserver Pod (TLS Termination):                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Container: k8s.gcr.io/echoserver:1.4                │   │
│  │ TLS Certificate: /etc/ssl/certs/tls.crt             │   │
│  │ Private Key: /etc/ssl/certs/tls.key                 │   │
│  │ Certificate Source: cert-manager Secret             │   │
│  │                                                     │   │
│  │ What echoserver returns:                            │   │
│  │ • Request headers and details                       │   │
│  │ • Pod information (name, namespace, IP)             │   │
│  │ • Node information                                  │   │
│  │ • TLS certificate details                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Key Point: Direct TLS termination in application       │
│  pod using cert-manager generated certificate              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 4: Create Certificate Resource

### **Create Certificate Resource Manually**

Since we're not using Ingress (which would automatically create the Certificate resource), we need to create it manually:

```bash
# Create Certificate resource for our domain
cat << EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: certmanagerdemo-tls-certificate
  namespace: certmanager-demo
spec:
  # Secret name where certificate will be stored
  secretName: certmanagerdemo-tls-secret
  
  # Reference to ClusterIssuer
  issuerRef:
    name: letsencrypt-dns01
    kind: ClusterIssuer
    group: cert-manager.io
  
  # Domain names for certificate
  dnsNames:
  - $DOMAIN
  
  # Certificate usage
  usages:
  - digital signature
  - key encipherment
  
  # Private key configuration
  privateKey:
    algorithm: RSA
    size: 2048
EOF
```

### **Understanding Certificate Resource**

```
┌─────────────────────────────────────────────────────────────┐
│              CERTIFICATE RESOURCE CONFIGURATION             │
│                                                             │
│  📜 Certificate Spec:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ secretName: certmanagerdemo-tls-secret              │   │
│  │ ↳ Kubernetes Secret where cert will be stored      │   │
│  │                                                     │   │
│  │ issuerRef: letsencrypt-dns01 (ClusterIssuer)       │   │
│  │ ↳ Which certificate authority to use               │   │
│  │                                                     │   │
│  │ dnsNames: [certmanagerdemo.srinman.com]            │   │
│  │ ↳ Domain names to include in certificate           │   │
│  │                                                     │   │
│  │ usages: [digital signature, key encipherment]      │   │
│  │ ↳ How certificate can be used                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🔄 What cert-manager does automatically:                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Sees Certificate resource creation               │   │
│  │ 2. Creates CertificateRequest                       │   │
│  │ 3. Creates Order (ACME protocol)                    │   │
│  │ 4. Creates Challenge (DNS-01)                       │   │
│  │ 5. Waits for manual DNS TXT record                  │   │
│  │ 6. Validates with Let's Encrypt                     │   │
│  │ 7. Stores certificate in Secret                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 5: DNS Configuration

### **Configure DNS A Record**

You need to create a DNS A record pointing your domain to the NGINX Ingress Controller IP:

```bash
# Display DNS record information for manual creation
cat << EOF

📋 DNS A RECORD CONFIGURATION REQUIRED:
=====================================

Domain: $DOMAIN
Record Type: A
Value: 128.85.229.216 (NGINX Ingress Controller IP)
TTL: 300 seconds (5 minutes)

🔗 Azure CLI Command for DNS Administrator:
az network dns record-set a add-record \\
  --resource-group <resource-group-name> \\
  --zone-name srinman.com \\
  --record-set-name certmanagerdemo \\
  --ipv4-address 128.85.229.216

📧 EMAIL TO DNS ADMINISTRATOR:
==============================
Subject: DNS A Record Required for NGINX Ingress - certmanagerdemo.srinman.com

Hi [DNS Administrator],

I need a DNS A record created for the NGINX Ingress Controller:

📋 DNS A RECORD (Required for Ingress access):
   DNS Zone: srinman.com
   Record Type: A
   Name: certmanagerdemo
   Value: $INGRESS_IP
   TTL: 300 seconds

This record points the domain to the NGINX Ingress public IP for SSL certificate automation.

Thanks for your help!

EOF
```

### **Verify DNS Resolution**

```bash
# Wait for DNS propagation and verify
echo "Testing DNS resolution..."
while true; do
    IP=$(dig +short $DOMAIN)
    if [ "$IP" = "$INGRESS_IP" ]; then
        echo "✅ DNS A record resolved correctly: $DOMAIN → $INGRESS_IP"
        break
    else
        echo "⏳ Waiting for DNS propagation... Current: $IP, Expected: $INGRESS_IP"
        sleep 30
    fi
done

# Test from multiple DNS servers
echo -e "\n=== Testing DNS Propagation ==="
dig @8.8.8.8 +short $DOMAIN     # Google DNS
dig @1.1.1.1 +short $DOMAIN     # Cloudflare DNS
dig @168.63.129.16 +short $DOMAIN # Azure DNS
```

---

## Step 6: Monitor Automatic Certificate Creation

### **Watch cert-manager Certificate Creation**

With the Ingress configured with the `cert-manager.io/cluster-issuer` annotation, cert-manager will automatically create the Certificate resource:

```bash
# Watch Certificate resource creation (happens automatically)
kubectl get certificates --namespace certmanager-demo --watch

# In another terminal, describe the certificate for details
kubectl describe certificate certmanagerdemo-tls-secret --namespace certmanager-demo
```

### **Monitor HTTP-01 Challenge Process**

```bash
# Watch Order resource (ACME certificate request)
kubectl get orders --namespace certmanager-demo --watch

# Watch Challenge resource (HTTP-01 challenge)
kubectl get challenges --namespace certmanager-demo --watch

# Get detailed challenge information
kubectl describe challenges --namespace certmanager-demo
```

### **Understanding HTTP-01 Challenge Flow**

```
┌─────────────────────────────────────────────────────────────┐
│               HTTP-01 CHALLENGE WITH NGINX INGRESS          │
│                                                             │
│  1️⃣ Ingress Created with TLS Configuration:                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • cert-manager.io/cluster-issuer annotation        │   │
│  │ • TLS section with secretName                      │   │
│  │ • NGINX ingress class specified                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  2️⃣ cert-manager Creates Certificate Resource:             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Automatically generated from Ingress TLS config  │   │
│  │ • References the specified ClusterIssuer           │   │
│  │ • Defines domain names and secret name             │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  3️⃣ HTTP-01 Challenge Created:                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Let's Encrypt generates challenge token           │   │
│  │ • cert-manager creates temporary ingress rule       │   │
│  │ • Challenge served at /.well-known/acme-challenge/  │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  4️⃣ Let's Encrypt Validates Domain (AUTOMATIC):            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • HTTP GET to domain/.well-known/acme-challenge/... │   │
│  │ • NGINX ingress routes request to cert-manager     │   │
│  │ • Challenge token verified automatically           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  5️⃣ Certificate Issued & Installed (AUTOMATIC):            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Let's Encrypt signs and delivers certificate     │   │
│  │ • cert-manager stores in Kubernetes Secret         │   │
│  │ • NGINX automatically uses certificate for TLS     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💡 Key Advantage: Fully automated with NO manual steps!  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Understanding cert-manager Resource Flow**

```
┌─────────────────────────────────────────────────────────────┐
│               CERT-MANAGER RESOURCE LIFECYCLE               │
│                                                             │
│  1️⃣ Certificate Resource Created:                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ User creates Certificate resource manually with     │   │
│  │ domain names and ClusterIssuer reference           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  2️⃣ CertificateRequest Created:                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ cert-manager controller sees Certificate resource  │   │
│  │ and automatically creates CertificateRequest       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  3️⃣ Order Created (ACME Protocol):                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ACME issuer creates Order resource representing    │   │
│  │ the ACME certificate order with Let's Encrypt     │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  4️⃣ Challenge Created (DNS-01):                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Order controller creates Challenge resource for    │   │
│  │ DNS-01 domain validation challenge                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  5️⃣ Manual DNS TXT Record (USER ACTION REQUIRED):         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Challenge controller waits for DNS TXT record     │   │
│  │ User must create TXT record manually              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  6️⃣ Certificate Issued & Secret Created:                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Let's Encrypt validates, issues certificate       │   │
│  │ cert-manager stores in Kubernetes Secret          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ▼                                  │
│  7️⃣ Application Uses TLS Secret:                           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Echoserver deployment mounts Secret as volume     │   │
│  │ Uses tls.crt and tls.key for HTTPS termination    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 7: Verify Certificate Issuance and Test HTTPS

### **Monitor Certificate Status**

```bash
# Check certificate status
kubectl get certificate --namespace certmanager-demo

# Look for Ready status:
# NAME                         READY   SECRET                       AGE
# certmanagerdemo-tls-secret   True    certmanagerdemo-tls-secret   21m

# Get detailed certificate information
kubectl describe certificate certmanagerdemo-tls-secret --namespace certmanager-demo

# Expected certificate details:
# Status:
#   Conditions:
#     Status:                True
#     Type:                  Ready
#   Not After:               2025-11-07T18:48:16Z (90 days from issue)
#   Not Before:              2025-08-09T18:48:17Z
#   Renewal Time:            2025-10-08T18:48:16Z (30 days before expiry)
```

### **Verify TLS Secret Creation**

```bash
# Check if cert-manager created the TLS secret
kubectl get secret certmanagerdemo-tls-secret --namespace certmanager-demo

# View secret contents (certificates and private key)
kubectl describe secret certmanagerdemo-tls-secret --namespace certmanager-demo

# Expected data keys:
# tls.crt (server certificate + chain)
# tls.key (private key)
# ca.crt  (CA certificate)
```

### **Test HTTPS Connection**

```bash
# Test HTTPS connection through NGINX Ingress
curl -I https://certmanagerdemo.srinman.com

# Expected response:
# HTTP/2 200
# server: nginx/1.21.x
# date: ...
# content-type: text/plain

# Test certificate details
echo | openssl s_client -connect certmanagerdemo.srinman.com:443 -servername certmanagerdemo.srinman.com 2>/dev/null | openssl x509 -noout -issuer -subject -dates

# Expected certificate information:
# issuer=C = US, O = Let's Encrypt, CN = R3
# subject=CN = certmanagerdemo.srinman.com
# notBefore=Aug  9 18:48:17 2025 GMT
# notAfter=Nov  7 18:48:16 2025 GMT

# Test detailed HTTPS connection
curl -v https://certmanagerdemo.srinman.com 2>&1 | head -20
```

### **Browser Testing**

1. **Navigate to your domain**: `https://certmanagerdemo.srinman.com`
2. **Check security indicators**:
   - ✅ Green lock icon
   - ✅ "Connection is secure"  
   - ✅ Certificate issued by "Let's Encrypt Authority R3"
   - ✅ Valid certificate chain
3. **View certificate details**: Click lock → Certificate → Details
   - Issuer: Let's Encrypt Authority R3
   - Subject: certmanagerdemo.srinman.com
   - Validity: Aug 9, 2025 to Nov 7, 2025 (90 days)
   - Subject Alternative Names: certmanagerdemo.srinman.com
4. **Echoserver Output**: The page will show detailed request information including:
   - Client IP address
   - Request headers (including X-Forwarded-For from NGINX Ingress)
   - Pod information (name, namespace, node)  
   - Server details showing HTTP (port 8080) backend communication

### **Verify Automatic Certificate Management**

```bash
# Check cert-manager logs for certificate processing
kubectl logs -n cert-manager deployment/cert-manager | tail -20

# Check NGINX ingress logs
kubectl logs -n ingress-nginx deployment/ingress-nginx-controller | tail -20

# Check ingress status
kubectl describe ingress echoserver-ingress --namespace certmanager-demo
```

---

## Step 8: Certificate Renewal and Lifecycle

### **Understanding Automatic Renewal**

cert-manager automatically handles certificate renewal:

```
┌─────────────────────────────────────────────────────────────┐
│              CERT-MANAGER AUTOMATIC RENEWAL                 │
│                                                             │
│  📅 Certificate Lifecycle:                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Day 0:  ✅ Certificate issued (90 days validity)    │   │
│  │ Day 60: 🔄 cert-manager checks renewal (30d left)   │   │
│  │ Day 67: 🚨 Automatic renewal triggered (23d left)   │   │
│  │ Day 67: ✅ New certificate issued and installed     │   │
│  │ Day 90: 🗑️ Old certificate would have expired      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🤖 Automation Benefits:                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ No manual intervention required                  │   │
│  │ ✅ Zero-downtime certificate updates                │   │
│  │ ✅ Automatic Secret updates                         │   │
│  │ ✅ Ingress controller picks up new certificates     │   │
│  │ ✅ Event-driven renewal process                     │   │
│  │ ✅ Built-in retry logic for failures                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Monitor Renewal Configuration**

```bash
# Check certificate renewal settings
kubectl get certificate certmanagerdemo-tls-certificate --namespace certmanager-demo -o yaml

# Look for renewBefore field (default: 2/3 of validity period = 60 days)
# spec:
#   renewBefore: 720h0m0s  # 30 days

# Check certificate expiration and renewal status
kubectl describe certificate certmanagerdemo-tls-certificate --namespace certmanager-demo

# Monitor cert-manager events
kubectl get events --namespace certmanager-demo --field-selector reason=Renewed
```

### **Test Renewal Process (Optional)**

```bash
# Force certificate renewal for testing (be careful with rate limits!)
kubectl annotate certificate certmanagerdemo-tls-certificate --namespace certmanager-demo \
    cert-manager.io/issue-temporary-certificate="true" --overwrite

# Watch the renewal process
kubectl get certificate certmanagerdemo-tls-certificate --namespace certmanager-demo --watch

# Check if new secret was created
kubectl describe secret certmanagerdemo-tls-secret --namespace certmanager-demo
```

---

## Step 9: Cleanup and Best Practices

### **No Manual DNS Record Cleanup Needed**

With HTTP-01 challenges, there are no temporary DNS TXT records to clean up! The NGINX ingress controller automatically handles all challenge routing.

### **Production Best Practices**

For production deployments, consider these improvements:

```bash
# 1. Use automated DNS provider integration instead of manual challenges
# Example ClusterIssuer with Azure DNS integration:
cat << 'EOF' > clusterissuer-azure-dns.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-azure-dns
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: snmanivel@gmail.com
    privateKeySecretRef:
      name: letsencrypt-azure-dns-private-key
    solvers:
    - dns01:
        azureDNS:
          clientID: <azure-client-id>
          clientSecretSecretRef:
            name: azure-dns-secret
            key: client-secret
          subscriptionID: <azure-subscription-id>
          tenantID: <azure-tenant-id>
          resourceGroupName: <azure-resource-group>
          hostedZoneName: srinman.com
EOF

# 2. Set up monitoring and alerting
kubectl apply -f - << EOF
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: cert-manager-metrics
  namespace: cert-manager
spec:
  selector:
    matchLabels:
      app.kubernetes.io/name: cert-manager
  endpoints:
  - port: tcp-prometheus-servicemonitor
    interval: 60s
    path: /metrics
EOF

# 3. Configure backup for certificates and keys
# Use Velero or similar for cluster backup including cert-manager resources
```

---

## Troubleshooting Common Issues

### **Challenge Stuck in Pending State**

```bash
# Check challenge details
kubectl describe challenges --namespace certmanager-demo

# Common issues for HTTP-01 challenges:
# 1. NSG/Firewall blocking Let's Encrypt validation traffic
# 2. DNS A record not pointing to correct NGINX Ingress IP
# 3. NGINX Ingress Controller not running or misconfigured

# Debug HTTP-01 challenge connectivity
curl -v http://certmanagerdemo.srinman.com/.well-known/acme-challenge/test
```

### **HTTP-01 Challenge Validation Failures (Most Common Issue)**

**🚨 ROOT CAUSE**: Network Security Group (NSG) or firewall blocking Let's Encrypt validation servers.

**📚 Reference**: [Let's Encrypt Integration Guide - Firewall Configuration](https://letsencrypt.org/docs/integration-guide/#firewall-configuration)

```bash
# Symptoms: HTTP-01 challenges fail with connection timeouts
kubectl get challenges --namespace certmanager-demo
# Shows: Status: pending, Reason: Waiting for http-01 challenge propagation

# Check challenge events for detailed error messages
kubectl describe challenges --namespace certmanager-demo

# Common error messages:
# - "Connection refused" or "Connection timeout"
# - "No route to host"
# - "Waiting for HTTP-01 challenge propagation"

# Verify NSG rules allow HTTP traffic from Internet
az network nsg rule list \
  --resource-group <your-resource-group> \
  --nsg-name <your-nsg-name> \
  --query "[?direction=='Inbound' && destinationPortRange=='80']"

# Test HTTP connectivity from external perspective
# (Run from a different network/machine outside your infrastructure)
curl -v http://certmanagerdemo.srinman.com/.well-known/acme-challenge/test-connectivity

# If this fails, your NSG is blocking Let's Encrypt validation traffic
```

#### **Fix NSG/Firewall Issues**

```bash
# Solution: Add NSG rule to allow HTTP traffic for ACME validation
az network nsg rule create \
  --resource-group <your-resource-group> \
  --nsg-name <your-nsg-name> \
  --name AllowHTTPForACME \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes Internet \
  --source-port-ranges '*' \
  --destination-address-prefixes '*' \
  --destination-port-ranges 80 \
  --description "Allow HTTP for Let's Encrypt ACME HTTP-01 challenges"

# After adding the rule, wait a few minutes and retry certificate issuance
kubectl delete certificate certmanagerdemo-tls-secret --namespace certmanager-demo
# cert-manager will automatically recreate it from the Ingress configuration
```

#### **Verify NSG Configuration**

```bash
# Check current NSG rules affecting HTTP traffic
az network nsg rule list \
  --resource-group <your-resource-group> \
  --nsg-name <your-nsg-name> \
  --query "[?destinationPortRange=='80' || destinationPortRange=='443'].[name,priority,access,direction,sourceAddressPrefix]" \
  --output table

# Ensure you have rules similar to:
# Name              Priority  Access  Direction  SourceAddressPrefix
# AllowHTTPForACME  100       Allow   Inbound    Internet
# AllowHTTPS        110       Allow   Inbound    Internet
```

### **Certificate Not Ready**

```bash
# Check certificate status and events
kubectl describe certificate certmanagerdemo-tls-certificate --namespace certmanager-demo

# Check related resources
kubectl get certificaterequest --namespace certmanager-demo
kubectl get order --namespace certmanager-demo
kubectl describe order --namespace certmanager-demo

# Check cert-manager controller logs
kubectl logs -n cert-manager deployment/cert-manager --tail=50
```

### **Echoserver Not Serving HTTPS**

```bash
# Check echoserver deployment
kubectl describe deployment echoserver --namespace certmanager-demo

# Verify TLS secret exists and is populated
kubectl get secret certmanagerdemo-tls-secret --namespace certmanager-demo
kubectl describe secret certmanagerdemo-tls-secret --namespace certmanager-demo

# Check echoserver logs
kubectl logs -n certmanager-demo deployment/echoserver --tail=50

# Test LoadBalancer service connectivity
kubectl describe service echoserver-service --namespace certmanager-demo

# Test pod connectivity directly
kubectl port-forward -n certmanager-demo deployment/echoserver 8080:8080
curl http://localhost:8080
```

### **LoadBalancer IP Issues**

```bash
# Check LoadBalancer service status
kubectl get svc -n certmanager-demo echoserver-service

# If external IP is pending, check cloud provider integration
kubectl describe svc -n certmanager-demo echoserver-service

# Verify DNS A record points to correct IP
dig +short $DOMAIN
kubectl get svc -n certmanager-demo echoserver-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## Understanding the Complete cert-manager Flow

### **Summary of Automated Process**

```
┌─────────────────────────────────────────────────────────────┐
│         COMPLETE CERT-MANAGER HTTP-01 LIFECYCLE             │
│                                                             │
│  Phase 1: PREPARATION                                      │
│  👤 User: Deploy cert-manager, NGINX Ingress Controller    │
│  🤖 Automated: Controller registration, ACME account setup │
│                                                             │
│  Phase 2: APPLICATION DEPLOYMENT                           │
│  👤 User: Deploy app, create Ingress with TLS annotations  │
│  🤖 Automated: Certificate resource auto-creation          │
│                                                             │
│  Phase 3: CERTIFICATE REQUEST                              │
│  🤖 Automated: CertificateRequest, Order, Challenge CRs    │
│  🏛️ Let's Encrypt: ACME protocol, HTTP-01 challenge       │
│                                                             │
│  Phase 4: DOMAIN VALIDATION (FULLY AUTOMATED)              │
│  🤖 Automated: NGINX serves challenge at /.well-known/     │
│  🏛️ Let's Encrypt: HTTP GET validation, no DNS required   │
│                                                             │
│  Phase 5: CERTIFICATE ISSUANCE                             │
│  🏛️ Let's Encrypt: Certificate signing, delivery          │
│  🤖 Automated: Secret creation, certificate storage        │
│                                                             │
│  Phase 6: TLS TERMINATION                                  │
│  🤖 Automated: NGINX Ingress picks up TLS secret          │
│  🌐 Client: HTTPS connections via NGINX with valid cert   │
│                                                             │
│  Phase 7: LIFECYCLE MANAGEMENT                             │
│  🤖 Automated: Renewal monitoring, certificate refresh     │
│  👤 User: Monitor cert-manager logs, handle failures       │
│                                                             │
│  💡 Key Innovation: Zero manual DNS intervention required │
│  with HTTP-01 challenges handled by NGINX Ingress         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Comparison with Previous Approaches**

| Aspect | Manual Process | certbot (Semi-Auto) | cert-manager (Full Auto) |
|--------|---------------|---------------------|--------------------------|
| **Platform** | Linux + OpenSSL | Linux command-line | ✅ Kubernetes-native |
| **Configuration** | Manual files | Command parameters | ✅ Declarative YAML |
| **Certificate Storage** | File system | /etc/letsencrypt/ | ✅ Kubernetes Secrets |
| **Renewal** | Full manual process | Cron/systemd timers | ✅ Controller reconciliation |
| **Integration** | Manual web server setup | Manual web server config | ✅ Automatic Ingress integration |
| **Scalability** | Single certificate | Single server | ✅ Multi-certificate, cluster-wide |
| **High Availability** | Manual clustering | Single point of failure | ✅ Kubernetes cluster resilience |
| **DNS Challenge** | Manual record creation | Manual record creation | ✅ Automated with HTTP-01 challenges |
| **Monitoring** | Manual log checking | Manual log checking | ✅ Kubernetes events & metrics |

### **Benefits of cert-manager Approach**

✅ **Kubernetes Integration**: Native resource management with kubectl
✅ **Declarative Configuration**: Infrastructure as Code with GitOps support  
✅ **Automatic Renewal**: Built-in controller reconciliation loop
✅ **High Availability**: Cluster-wide certificate management
✅ **Event-Driven**: Responds to Ingress changes automatically
✅ **Extensible**: Support for multiple certificate authorities and DNS providers
✅ **Observable**: Rich events, metrics, and status reporting
✅ **Scalable**: Manages hundreds of certificates across multiple namespaces

---

## Key Terminology Review

Building on concepts from previous guides:

- **🎛️ cert-manager**: Kubernetes controller for automated certificate management
- **🌐 ClusterIssuer**: Cluster-wide certificate authority configuration
- **📜 Certificate**: Kubernetes custom resource defining certificate requirements
- **🔍 Challenge**: Kubernetes resource representing ACME domain validation
- **📋 Order**: Kubernetes resource representing ACME certificate request
- **🔐 TLS Secret**: Kubernetes Secret storing certificate and private key
- **🌉 Ingress**: Kubernetes resource configuring HTTP/HTTPS routing with TLS
- **⚖️ LoadBalancer**: Kubernetes service type exposing applications with public IP
- **🤖 Controller Reconciliation**: Continuous desired state enforcement
- **📊 Custom Resource Definition (CRD)**: Extension of Kubernetes API for cert-manager

---

---

## ✅ Implementation Success Summary

**Congratulations!** You have successfully implemented fully automated certificate management using cert-manager with HTTP-01 challenges on AKS. Here's what you achieved:

### **🎯 Working Configuration**
- **NGINX Ingress Controller**: `128.85.229.216` (LoadBalancer with external IP)
- **ClusterIssuer**: `letsencrypt-http01` (Ready=True)
- **Certificate**: `certmanagerdemo-tls-secret` (Ready=True)
- **Domain**: `https://certmanagerdemo.srinman.com` (✅ HTTPS working)
- **Validity Period**: August 9, 2025 to November 7, 2025 (90 days)
- **Auto-Renewal**: Scheduled for October 8, 2025 (30 days before expiry)

### **🚀 Key Achievements**
- ✅ **Zero Manual DNS Management**: No TXT record creation required
- ✅ **Fully Automated Validation**: HTTP-01 challenges handled by NGINX
- ✅ **Certificate Auto-Provisioning**: Created from Ingress annotations
- ✅ **Working HTTPS**: Trusted certificate from Let's Encrypt R3
- ✅ **Automatic Renewal**: Built-in lifecycle management

### **🏆 Technical Benefits Realized**
- **Kubernetes-Native**: Declarative YAML configuration
- **High Availability**: Cluster-wide certificate management
- **Scalable**: Multi-certificate support across namespaces
- **Observable**: Rich events, metrics, and status reporting
- **Maintainable**: GitOps-compatible infrastructure as code

### **🎓 Critical Lessons Learned**

**⚠️ Most Important**: **Network Security Group (NSG) configuration is the #1 cause of HTTP-01 challenge failures**
- Let's Encrypt validation servers use unpublished IP ranges that change without notice
- You **MUST** allow inbound HTTP (port 80) traffic from Internet (`0.0.0.0/0`)  
- Attempting to restrict to specific IP addresses **WILL** break certificate issuance
- This was the root cause of initial challenges in this implementation

**🔧 Key Success Factors**:
1. **NSG Rules**: Allow ports 80 and 443 from Internet for Let's Encrypt validation
2. **DNS Configuration**: A record must point to NGINX Ingress IP (not application LoadBalancer)
3. **HTTP-01 vs DNS-01**: HTTP-01 challenges are fully automated (no manual DNS TXT records)
4. **Challenge Validation**: Monitor `kubectl get challenges` for real-time status
5. **Certificate Auto-Creation**: Ingress annotations automatically trigger certificate generation

---

## Production Considerations

This cert-manager approach is ideal for:
- **Kubernetes-native applications** requiring automated certificate management
- **Microservices architectures** with multiple TLS endpoints  
- **GitOps workflows** with declarative certificate configuration
- **High-availability environments** requiring automatic renewal
- **Multi-tenant clusters** with namespace isolation

For enterprise production environments, consider:
- **Automated DNS provider integration** (Azure DNS, Route53, CloudFlare)
- **Private certificate authorities** for internal services
- **Certificate monitoring and alerting** via Prometheus/Grafana
- **Backup and disaster recovery** for cert-manager configuration and secrets
- **Network policies** for cert-manager controller security
- **RBAC policies** for cert-manager service accounts

The cert-manager approach represents the evolution from manual certificate management to fully automated, cloud-native certificate lifecycle management!
