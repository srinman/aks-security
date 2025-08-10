# Cert-Manager Troubleshooting Guide

This document provides a comprehensive troubleshooting workflow for cert-manager issues on AKS, including all diagnostic commands and solutions used to resolve certificate issuance problems.

## Problem Statement

**Issue**: Certificate issuance failing with ACME challenge timeout errors
**Error Message**: `Timeout during connect (likely firewall problem)`
**Domain**: `aksdemoapp.srinman.com`
**Environment**: AKS cluster with NGINX ingress controller

## Step 1: Initial Certificate Status Check

### Check Certificate Status
```bash
# Get current certificate status
kubectl get certificate -n default

# Get detailed certificate information
kubectl describe certificate example-tls-secret -n default
```

**Expected Output Issues**:
- Certificate shows `READY: False`
- Status shows "Failed to wait for order resource" with "invalid" state

### Check Certificate Request
```bash
# Check certificate request status
kubectl get certificaterequest -n default
kubectl describe certificaterequest -n default
```

### Check ACME Challenge Status
```bash
# List active challenges
kubectl get challenge -n default

# Get detailed challenge information
kubectl describe challenge -n default
```

**Key Error Found**:
```
Reason: Error accepting authorization: acme: authorization error for aksdemoapp.srinman.com: 
400 urn:ietf:params:acme:error:connection: 172.175.33.12: 
Fetching http://aksdemoapp.srinman.com/.well-known/acme-challenge/TOKEN: 
Timeout during connect (likely firewall problem)
```

## Step 2: Infrastructure Verification

### Check Ingress Controller Service
```bash
# Verify ingress controller service and external IP
kubectl get service -n ingress-nginx

# Expected output should show LoadBalancer with external IP
# nginx-ingress-ingress-nginx-controller   LoadBalancer   10.0.170.155   172.175.33.12   80:30750/TCP,443:32627/TCP
```

### Check DNS Resolution
```bash
# Verify DNS resolution
nslookup aksdemoapp.srinman.com

# Alternative DNS check
dig aksdemoapp.srinman.com
```

**Expected**: DNS should resolve to the ingress external IP (172.175.33.12)

### Check Ingress Resource
```bash
# Check if ingress resource exists
kubectl get ingress -n default

# Get detailed ingress information
kubectl describe ingress example-ingress -n default
```

**Issue Found**: If no ingress resource exists, ACME challenges cannot be routed properly.

## Step 3: Network Connectivity Testing

### Test External IP Connectivity
```bash
# Test direct IP access (this was failing)
curl -I http://172.175.33.12

# Test with domain
curl -I http://aksdemoapp.srinman.com
```

**Problem**: Both commands resulted in connection timeouts from external sources.

### Test Internal Cluster Connectivity
```bash
# Test if ingress works internally
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- \
  curl -I http://nginx-ingress-ingress-nginx-controller.ingress-nginx.svc.cluster.local

# Test with proper host header internally
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- \
  curl -H "Host: aksdemoapp.srinman.com" -I http://nginx-ingress-ingress-nginx-controller.ingress-nginx.svc.cluster.local
```

**Result**: Internal connectivity worked fine (404 or redirect responses), confirming the issue was with external access.

### Check Ingress Controller Pods
```bash
# Verify ingress controller pods are running
kubectl get pods -n ingress-nginx

# Check pod details if needed
kubectl describe pod -n ingress-nginx
```

### Check Service Endpoints
```bash
# Verify service has proper endpoints
kubectl get endpoints nginx-ingress-ingress-nginx-controller -n ingress-nginx
```

## Step 4: Azure Infrastructure Analysis

### Get AKS Cluster Information
```bash
# Get the node resource group (needed for NSG checks)
az aks show --name aksacns --resource-group aksrg --query "nodeResourceGroup" -o tsv
# Output: MC_aksrg_aksacns_eastus2
```

### Check Network Security Groups
```bash
# List NSGs in the node resource group
az network nsg list --resource-group MC_aksrg_aksacns_eastus2 --query "[].name" -o table

# Check NSG rules for HTTP/HTTPS traffic
az network nsg rule list --resource-group MC_aksrg_aksacns_eastus2 \
  --nsg-name aks-agentpool-11546080-nsg \
  --query "[].{Name:name,Priority:priority,Direction:direction,Access:access,Protocol:protocol,SourcePortRange:sourcePortRange,DestinationPortRange:destinationPortRange,SourceAddressPrefix:sourceAddressPrefix}" \
  -o table

# Get detailed rule information
az network nsg rule show --resource-group MC_aksrg_aksacns_eastus2 \
  --nsg-name aks-agentpool-11546080-nsg \
  --name k8s-azure-lb_allow_IPv4_556f7044ec033071ec0dfcf7cd85bc93
```

**Finding**: NSG rules were correctly configured to allow ports 80 and 443 from Internet to the specific IP.

### Check Azure Load Balancer
```bash
# List load balancers in node resource group
az network lb list --resource-group MC_aksrg_aksacns_eastus2 --query "[].{name:name,location:location}" -o table

# Check load balancer frontend IPs
az network lb frontend-ip list --lb-name kubernetes --resource-group MC_aksrg_aksacns_eastus2 -o table
```

### Check Service Configuration Details
```bash
# Get detailed service information
kubectl describe service nginx-ingress-ingress-nginx-controller -n ingress-nginx

# Check current traffic policy
kubectl get service nginx-ingress-ingress-nginx-controller -n ingress-nginx -o yaml | grep externalTrafficPolicy
```

**Key Finding**: Service was using `externalTrafficPolicy: Cluster` which can cause connectivity issues with Azure Load Balancer.

## Step 5: External Connectivity Verification

### Test from Different Sources
```bash
# Test from Azure Cloud Shell
curl -I http://172.175.33.12

# Test from local machine/different network
curl -I http://172.175.33.12
```

**Result**: Both external tests (Azure Cloud Shell and home MacBook) resulted in connection timeouts, confirming the load balancer was not accessible from the internet.

### Test with Host Header from Internal Pod
```bash
# Test specific domain routing
kubectl run test-pod --rm -it --image=curlimages/curl --restart=Never -- \
  curl -H "Host: aksdemoapp.srinman.com" -I http://172.175.33.12
```

**Result**: This worked internally and returned proper HTTP 308 redirect to HTTPS.

## Step 6: Solution Implementation

### Root Cause Identified
The issue was **Azure LoadBalancer with `externalTrafficPolicy: Cluster`** preventing external connectivity to the ingress controller.

### Solution: Change External Traffic Policy
```bash
# Patch the service to use Local traffic policy
kubectl patch service nginx-ingress-ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"externalTrafficPolicy":"Local"}}'

# Verify the change
kubectl get service nginx-ingress-ingress-nginx-controller -n ingress-nginx \
  -o yaml | grep externalTrafficPolicy
```

### Verify Connectivity After Fix
```bash
# Wait for load balancer reconfiguration
sleep 30

# Test external connectivity
curl -I --connect-timeout 10 http://172.175.33.12

# Test with proper host header
curl -H "Host: aksdemoapp.srinman.com" -I http://172.175.33.12
```

**Result**: After the traffic policy change:
- Direct IP access: `HTTP/1.1 404 Not Found` (expected for NGINX without proper routing)
- With host header: `HTTP/1.1 308 Permanent Redirect` (expected redirect to HTTPS)

## Step 7: Certificate Cleanup and Retry

### Clean Up Failed Certificate Resources
```bash
# Delete the failed certificate
kubectl delete certificate example-tls-secret -n default

# Delete certificate secret if it exists
kubectl delete secret example-tls-secret -n default

# Clean up failed challenges
kubectl delete challenge --all -n default
```

### Monitor New Certificate Creation
```bash
# Watch certificate creation (the ingress will automatically trigger a new request)
kubectl get certificate -n default -w

# Check certificate status
kubectl get certificate -n default

# Get detailed certificate information
kubectl describe certificate example-tls-secret -n default
```

**Success Result**:
```
NAME                 READY   SECRET               AGE
example-tls-secret   True    example-tls-secret   31s
```

## Step 8: Final Verification

### Verify HTTPS Functionality
```bash
# Test HTTPS access (use -k for staging certificates)
curl -H "Host: aksdemoapp.srinman.com" -I -k https://172.175.33.12

# Check certificate secret contents
kubectl get secret example-tls-secret -n default -o yaml

# Verify certificate details
kubectl describe certificate example-tls-secret -n default
```

**Success Indicators**:
- Certificate status: `Ready: True`
- HTTPS response: `HTTP/2 200`
- Certificate valid until: October 28, 2025 (3 months from issuance)

## Monitoring and Maintenance Commands

### Regular Certificate Monitoring
```bash
# Check all certificates across namespaces
kubectl get certificates --all-namespaces

# Monitor cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager -f

# Check for any challenges or issues
kubectl get certificates,certificaterequests,challenges,orders --all-namespaces
```

### Certificate Renewal Testing
```bash
# Force certificate renewal (for testing)
kubectl annotate certificate CERT_NAME -n NAMESPACE \
  cert-manager.io/issue-temporary-certificate="true" --overwrite

# Monitor renewal process
kubectl describe certificate CERT_NAME -n NAMESPACE
```

## Common Issues and Quick Fixes

### 1. LoadBalancer Connectivity Issues
```bash
# Check and fix traffic policy
kubectl patch service nginx-ingress-ingress-nginx-controller -n ingress-nginx \
  -p '{"spec":{"externalTrafficPolicy":"Local"}}'
```

### 2. Certificate Stuck in Pending
```bash
# Reset certificate
kubectl delete certificate CERT_NAME -n NAMESPACE
kubectl delete secret SECRET_NAME -n NAMESPACE
# Wait for automatic recreation via ingress
```

### 3. ACME Challenge Failures
```bash
# Check ingress exists and is accessible
kubectl get ingress -n NAMESPACE
curl -H "Host: YOUR_DOMAIN" -I http://EXTERNAL_IP

# Verify DNS resolution
nslookup YOUR_DOMAIN
```

### 4. Rate Limiting Issues
```bash
# Switch to staging issuer for testing
kubectl patch certificate CERT_NAME -n NAMESPACE \
  --type='merge' -p='{"spec":{"issuerRef":{"name":"letsencrypt-staging"}}}'
```

## Summary of Key Learnings

1. **External Traffic Policy**: AKS LoadBalancer requires `externalTrafficPolicy: Local` for reliable external connectivity
2. **Ingress Requirement**: ACME HTTP-01 challenges require a properly configured ingress resource
3. **DNS vs Connectivity**: DNS resolution success doesn't guarantee network connectivity
4. **Internal vs External**: Always test both internal cluster connectivity and external internet connectivity
5. **Staging First**: Use Let's Encrypt staging environment for testing to avoid rate limits

## Troubleshooting Workflow Summary

1. Check certificate/challenge status
2. Verify ingress controller and service configuration
3. Test DNS resolution
4. Test internal cluster connectivity
5. Test external connectivity
6. Check Azure infrastructure (NSG, Load Balancer)
7. Apply fixes (usually traffic policy changes)
8. Clean up failed resources
9. Monitor new certificate issuance
10. Verify final HTTPS functionality

This workflow successfully resolved the cert-manager connectivity issues and resulted in successful certificate issuance.
