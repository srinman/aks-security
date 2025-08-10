# Cert-Manager Installation and Configuration on AKS

This guide provides step-by-step instructions to install and configure cert-manager on Azure Kubernetes Service (AKS) with manual DNS management.

## Prerequisites

- AKS cluster running and accessible via kubectl
- kubectl configured to access your AKS cluster
- Helm 3.x installed
- Domain name with access to DNS management
- Azure CLI installed and logged in

## Step 1: Install cert-manager using Helm

First, add the cert-manager Helm repository and update it:

```bash
# Add the cert-manager Helm repository
helm repo add jetstack https://charts.jetstack.io

# Update Helm repositories
helm repo update
```

Create the cert-manager namespace and install cert-manager:

```bash
# Create cert-manager namespace
kubectl create namespace cert-manager

# Install cert-manager with CRDs
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.3 \
  --set installCRDs=true \
  --set global.leaderElection.namespace=cert-manager
```

Verify the installation:

```bash
# Check if cert-manager pods are running
kubectl get pods -n cert-manager

# Verify cert-manager CRDs are installed
kubectl get crd | grep cert-manager
```

## Step 2: Create a ClusterIssuer for Let's Encrypt

Create a ClusterIssuer that will be used to issue certificates from Let's Encrypt:

```bash
# Create ClusterIssuer for Let's Encrypt staging (for testing)
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    server: https://acme-staging-v02.api.letsencrypt.org/directory
    email: snmanivel@gmail.com  # Replace with your email
    privateKeySecretRef:
      name: letsencrypt-staging
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

Create a ClusterIssuer for Let's Encrypt production:

```bash
# Create ClusterIssuer for Let's Encrypt production
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: snmanivel@gmail.com  # Replace with your email
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

Verify the ClusterIssuers:

```bash
# Check ClusterIssuers status
kubectl get clusterissuer
kubectl describe clusterissuer letsencrypt-staging
kubectl describe clusterissuer letsencrypt-prod
```

## Step 3: Install NGINX Ingress Controller (if not already installed)

cert-manager needs an ingress controller to handle HTTP01 challenges:

```bash
# Add NGINX ingress Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install NGINX ingress controller
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer
```

Get the external IP of the ingress controller:

```bash
# Get the external IP (may take a few minutes)
kubectl get service -n ingress-nginx nginx-ingress-ingress-nginx-controller
```

## Step 4: Manual DNS Configuration

**🚨 IMPORTANT: Manual DNS Entry Required**

Before proceeding with certificate creation, you must:

1. **Note the External IP** from the previous step
2. **Add DNS A Record**: Create an A record in your DNS provider pointing your domain to the ingress controller's external IP
   ```
   Type: A
   Name: your-domain.com (or subdomain)
   Value: <EXTERNAL-IP-FROM-INGRESS>
   TTL: 300 (or as per your DNS provider's recommendation)
   ```
3. **Wait for DNS Propagation**: This can take 5-60 minutes depending on your DNS provider
4. **Verify DNS Resolution**:
   ```bash
   # Test DNS resolution
   nslookup your-domain.com
   # or
   dig your-domain.com
   ```

## Step 5: Create a Certificate for a New Domain

Once DNS is properly configured, create a certificate:

### Method 1: Using Certificate Resource Directly

```bash
# Create a certificate resource
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
  namespace: default  # Change to your application namespace
spec:
  secretName: example-tls-secret
  issuerRef:
    name: letsencrypt-staging  # Use letsencrypt-prod for production
    kind: ClusterIssuer
  dnsNames:
  - aksdemoapp.srinman.com  # Replace with your actual domain
EOF
```

### Method 2: Using Ingress with Annotations (Recommended)

```bash
# Create an ingress with cert-manager annotations
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: example-ingress
  namespace: default  # Change to your application namespace
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-staging  # Use letsencrypt-prod for production
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - aksdemoapp.srinman.com  # Replace with your actual domain
    secretName: example-tls-secret
  rules:
  - host: aksdemoapp.srinman.com  # Replace with your actual domain
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-app  # Replace with your service name
            port:
              number: 80
EOF
```

## Step 6: Monitor Certificate Issuance

Check the certificate status:

```bash
# Check certificate status
kubectl get certificate -n default
kubectl describe certificate example-tls -n default

# Check certificate request
kubectl get certificaterequest -n default
kubectl describe certificaterequest -n default

# Check ACME challenge
kubectl get challenge -n default
kubectl describe challenge -n default
```

View cert-manager logs for troubleshooting:

```bash
# View cert-manager controller logs
kubectl logs -n cert-manager -l app=cert-manager -f

# View cert-manager webhook logs
kubectl logs -n cert-manager -l app=webhook -f
```

## Step 7: Verify SSL Certificate

Once the certificate is issued successfully:

```bash
# Check the secret containing the certificate
kubectl get secret example-tls-secret -n default -o yaml

# Test the SSL certificate
curl -I https://your-domain.com

# Or test with openssl
openssl s_client -connect your-domain.com:443 -servername your-domain.com
```

## Step 8: Switch to Production (After Testing)

Once you've verified everything works with staging certificates:

1. **Update your ClusterIssuer reference** from `letsencrypt-staging` to `letsencrypt-prod`
2. **Delete the existing certificate** to force renewal:
   ```bash
   kubectl delete certificate example-tls -n default
   kubectl delete secret example-tls-secret -n default
   ```
3. **Reapply your certificate or ingress** with the production issuer
4. **Monitor the new certificate issuance**

## Troubleshooting

### Common Issues:

1. **DNS not resolving**: Ensure DNS A record is properly configured and propagated
2. **Challenge failures**: Check ingress controller and firewall settings
3. **Rate limits**: Let's Encrypt has rate limits; use staging for testing
4. **LoadBalancer IP not accessible**: Azure Load Balancer IP timeouts from external connections

### LoadBalancer Connectivity Issues

If you're getting timeouts when accessing the LoadBalancer IP externally:

#### Problem: LoadBalancer IP times out
```bash
# These commands will timeout:
curl -I http://172.175.33.12
curl -I http://your-domain.com
```

#### Root Cause Analysis:
```bash
# Check if ingress works internally (should work)
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- curl -H "Host: your-domain.com" -I http://nginx-ingress-ingress-nginx-controller.ingress-nginx.svc.cluster.local

# Check LoadBalancer service
kubectl get service -n ingress-nginx nginx-ingress-ingress-nginx-controller

# Verify NSG rules allow HTTP/HTTPS
az network nsg rule list --resource-group MC_RESOURCE_GROUP_NODE --nsg-name NSG_NAME --query "[?destinationPortRanges[?contains(@,'80')] || destinationPortRanges[?contains(@,'443')]]"
```

#### Solution 1: Use externalTrafficPolicy Local
```bash
# Patch the service to use Local traffic policy
kubectl patch service nginx-ingress-ingress-nginx-controller -n ingress-nginx -p '{"spec":{"externalTrafficPolicy":"Local"}}'

# Verify the change
kubectl get service nginx-ingress-ingress-nginx-controller -n ingress-nginx -o yaml | grep externalTrafficPolicy
```

#### Solution 2: Recreate with specific annotations
```bash
# Delete and recreate the ingress controller with Azure-specific annotations
helm uninstall nginx-ingress -n ingress-nginx

# Reinstall with Azure Load Balancer annotations
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.replicaCount=2 \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/azure-load-balancer-health-probe-request-path"=/healthz \
  --set controller.service.externalTrafficPolicy=Local
```

#### Solution 3: Check Azure Load Balancer Backend Pool
```bash
# Get the Azure Load Balancer name
az network lb list --resource-group MC_RESOURCE_GROUP_NODE --query "[].name" -o table

# Check backend pool configuration
az network lb address-pool list --lb-name kubernetes --resource-group MC_RESOURCE_GROUP_NODE

# Check load balancer rules
az network lb rule list --lb-name kubernetes --resource-group MC_RESOURCE_GROUP_NODE -o table
```

#### Solution 4: Enable Azure Load Balancer Diagnostics
```bash
# Create a public IP with specific settings
az network public-ip create \
  --resource-group MC_RESOURCE_GROUP_NODE \
  --name nginx-ingress-pip \
  --sku Standard \
  --allocation-method Static

# Get the IP address
PIP_IP=$(az network public-ip show --resource-group MC_RESOURCE_GROUP_NODE --name nginx-ingress-pip --query ipAddress -o tsv)

# Update the service to use the specific public IP
kubectl annotate service nginx-ingress-ingress-nginx-controller -n ingress-nginx \
  service.beta.kubernetes.io/azure-load-balancer-resource-group=MC_RESOURCE_GROUP_NODE

kubectl patch service nginx-ingress-ingress-nginx-controller -n ingress-nginx -p '{"spec":{"loadBalancerIP":"'$PIP_IP'"}}'
```

#### Verification Steps:
```bash
# Wait for LoadBalancer to get the new IP
kubectl get service -n ingress-nginx nginx-ingress-ingress-nginx-controller -w

# Test connectivity from external source
curl -I http://NEW_EXTERNAL_IP

# Test with domain
curl -H "Host: your-domain.com" -I http://NEW_EXTERNAL_IP

# Once external connectivity works, retry certificate
kubectl delete certificate CERT_NAME -n NAMESPACE
kubectl delete secret SECRET_NAME -n NAMESPACE
# Reapply your ingress/certificate
```

### Useful Commands:

```bash
# Check all cert-manager resources
kubectl get certificates,certificaterequests,challenges,orders --all-namespaces

# Reset certificate (force renewal)
kubectl delete certificate CERT_NAME -n NAMESPACE
kubectl delete secret SECRET_NAME -n NAMESPACE

# Check cert-manager version
kubectl get deployment -n cert-manager cert-manager -o jsonpath='{.spec.template.spec.containers[0].image}'
```

## Additional DNS Reminders

**Before creating certificates for new domains:**

1. ✅ **Add DNS A Record** pointing to ingress external IP
2. ✅ **Verify DNS propagation** using `nslookup` or `dig`
3. ✅ **Test HTTP connectivity** to ensure ingress is reachable
4. ✅ **Use staging issuer first** to avoid rate limits
5. ✅ **Monitor certificate creation** process
6. ✅ **Switch to production issuer** after successful testing

Remember: DNS changes can take time to propagate globally (5-60 minutes), so be patient before troubleshooting certificate issues.
