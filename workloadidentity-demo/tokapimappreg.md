# Workload Identity - step by step   


## This is a variation of the workload identity setup where we use an app registration (instead of 'user-assigned managed identity') and a federated credential for the service account in the namespace. 

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
k get pods -n testns
k logs pythonpod -n testns
k delete pod pythonpod -n testns --force








