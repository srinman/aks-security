# Workload Identity - Step by Step   - Using managed identity and federated credential



##  Few things to note before we start


tried to remove variable names and use the actual values for more readability.   

Following values are hardcoded for the sake of simplicity.  
cluster name: aks  
resource group: aksrg  
namespace: testns  
service account: testsa  
storage account name: srinmanwkldstorage.blob.core.windows.net


## Create a new AKS cluster with OIDC issuer enabled and workload identity enabled

```bash
az aks create -g aksrg -n aks --enable-oidc-issuer --enable-workload-identity  

export AKS_OIDC_ISSUER="$(az aks show -n aks -g aksrg --query "oidcIssuerProfile.issuerUrl" --output tsv)"
```

## Create a user assigned managed identity and a federated credential

```bash
az identity create --name aksappmi --resource-group aksrg --location eastus2

az identity federated-credential create --name fedaksappmi --identity-name aksappmi --resource-group aksrg --issuer AKS_OIDC_ISSUER --subject system:serviceaccount:testns:testsa --audience api://AzureADTokenExchange 

export UAMI_CLIENTID="$(az identity show -n aksappmi -g aksrg --query 'clientId' --output tsv)"
```

## Create a namespace and a service account in the namespace  

```bash
az aks get-credentials -g aksrg -n aks
k create ns testns 
```

## Create a service account in the namespace  
```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${UAMI_CLIENTID}"
  name: testsa
  namespace: testns
EOF
```

## Create container image and run the application   

Use Dockerfile provided in the repo to build the image and push it to your container registry.  Use az acr build for building the image.    

```bash
az acr build -t srinmantest.azurecr.io/wkldtest:v1 -r srinmantest -f Dockerfile .
```

This ACR has to be integrated with the AKS cluster.  Use the following command to integrate the ACR with AKS, if it's not done already.  

```bash
az aks update -n aks -g aksrg --attach-acr srinmantest
```  

Yaml for deploying the pod.  
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pythonpod
  namespace: testns
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: testsa
  containers:
  - name: blob-creator
    image: srinmantest.azurecr.io/wkldtest:sdktok
    imagePullPolicy: Always
    env: 
    - name: STORAGE_ACCOUNT_URL
      value: "https://srinmanwkldstorage.blob.core.windows.net/"
EOF
```

Use policysample.xml to validate the token in APIM.  

Review logs and delete the pod.  

```bash
k get pods -n testns  
k logs pythonpod -n testns  
k delete pod pythonpod -n testns --force   
```




# Workload Identity - Step by Step  - Using app registration and federated credential

**AKS only at this time**
This may be supported in ACA in the future.  This is a variation of the workload identity setup where we use an app registration (instead of 'user-assigned managed identity') and a federated credential for the service account in the namespace.


Created app registration and added federated credential for testsa service account in testns namespace.  This is to demonstrate the use of federated credential for a service account in a namespace.

id is 'object id' of the app registration.  This is used to get the app id of the app registration.  

```bash
export APPREG_CLIENTID="$(az ad sp show --id e02758db-e5b5-420b-95e7-3d9686e7b3d8 --query 'appId' --output tsv)"
```

## Create a namespace and a service account in the namespace  

```bash
az aks get-credentials -g aksrg -n aks
k create ns testns 
```

## Create a service account in the namespace  
```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  annotations:
    azure.workload.identity/client-id: "${APPREG_CLIENTID}"
  name: testsa
  namespace: testns
EOF
```

## Create container image and run the application   

Use Dockerfile provided in the repo to build the image and push it to your container registry.  Use az acr build for building the image.    

```bash
az acr build -t srinmantest.azurecr.io/wkldtest:dacapimsdk -r srinmantest .
az acr build -t srinmantest.azurecr.io/wkldtest:resttok -r srinmantest -f Dockerfile_resttok .
az acr build -t srinmantest.azurecr.io/wkldtest:sdktok -r srinmantest -f Dockerfile_sdktok .
```

This ACR has to be integrated with the AKS cluster.  Use the following command to integrate the ACR with AKS, if it's not done already.  

```bash
az aks update -n aks -g aksrg --attach-acr srinmantest
```  

Yaml for deploying the pod.  
```bash
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: pythonpod
  namespace: testns
  labels:
    azure.workload.identity/use: "true"
spec:
  serviceAccountName: testsa
  containers:
  - name: blob-creator
    image: srinmantest.azurecr.io/wkldtest:sdktok
    imagePullPolicy: Always
EOF
```

appid changes with app registration. so change the appid in the policy file.  
Use policysample_appreg.xml to validate the token in APIM.    


Review logs and delete the pod.  

```bash
k get pods -n testns  
k logs pythonpod -n testns  
k delete pod pythonpod -n testns --force   
```









