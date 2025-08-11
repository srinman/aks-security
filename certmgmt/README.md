# Certificate Management for AKS Security

This directory contains comprehensive guides and resources for certificate management in Azure Kubernetes Service (AKS) environments, covering everything from basic concepts to advanced automation techniques.

## 📚 Learning Path

### **Start Here: Complete Learning Guide**
- **[cert-management-basics-to-advanced.md](./cert-management-basics-to-advanced.md)** - **📖 MAIN GUIDE**
  - Comprehensive overview of certificate management from basics to advanced
  - RFC 8555 ACME protocol explanation and context
  - Learning path guidance and exercise progression
  - Production considerations and best practices

---

## 🎯 Laboratory Exercises (Ordered Sequence)

### **1. Foundation Level**
- **[cert-basics.md](./cert-basics.md)** - Certificate Fundamentals
  - X.509 certificate structure and components
  - PKI concepts and trust relationships
  - Certificate inspection and validation
  - **Prerequisites**: Basic understanding of cryptography
  - **Duration**: 2-3 hours

### **2. Practical Implementation**
- **[cert-generation-basics.md](./cert-generation-basics.md)** - Manual Certificate Creation
  - OpenSSL command-line usage
  - Private key generation and CSR creation
  - Self-signed certificate generation
  - **Prerequisites**: Complete cert-basics.md
  - **Duration**: 3-4 hours

### **3. Automation Introduction**
- **[cert-generation-semiautomated.md](./cert-generation-semiautomated.md)** - Semi-Automated Solutions
  - Scripted certificate operations
  - Batch certificate handling
  - Template-based certificate management
  - **Prerequisites**: Complete cert-generation-basics.md
  - **Duration**: 2-3 hours

### **4. Production Automation**
- **[cert-generation-automatedwithcertmanager.md](./cert-generation-automatedwithcertmanager.md)** - ACME with cert-manager
  - cert-manager deployment in AKS
  - Let's Encrypt ACME integration
  - HTTP-01 challenge automation
  - Ingress integration and certificate lifecycle
  - **Prerequisites**: AKS cluster, basic Kubernetes knowledge
  - **Duration**: 4-5 hours

### **5. Advanced Implementation**
- **[cert-generation-automatedwithcm-e2etls.md](./cert-generation-automatedwithcm-e2etls.md)** - End-to-End TLS Automation
  - Internal CA deployment with cert-manager
  - Two-tier certificate architecture
  - Backend TLS termination
  - Complete end-to-end encryption
  - **Prerequisites**: Complete previous exercises
  - **Duration**: 5-6 hours

---

## � Issuer Mapping (based on [Issuers](https://cert-manager.io/docs/configuration/issuers/))

| Lab | Primary issuer type | Notes |
|-----|----------------------|-------|
| cert-generation-basics.md | CA | Manual root CA is created via self-signed cert, then used to sign leaf certs (equivalent to cert-manager CA issuer behavior). |
| cert-generation-semiautomated.md | ACME | Uses certbot with Let’s Encrypt (DNS-01). |
| cert-generation-automatedwithcertmanager.md | ACME | Uses cert-manager with Let’s Encrypt (HTTP-01) via ClusterIssuer. |
| cert-generation-automatedwithcm-e2etls.md | CA | Uses SelfSigned to bootstrap a root, then CA ClusterIssuer for internal mTLS; also defines an ACME ClusterIssuer for public ingress. |
| cert-basics.md | N/A | Conceptual fundamentals (no issuer). |

Notes
- “Vault” issuer is not covered by current labs.
- Where both ACME and CA are present, the table lists the primary issuer focus for the exercise.

---

## �🛠️ Configuration Files

### **cert-manager Configurations**
- **[clusterissuer-http01-simple.yaml](./clusterissuer-http01-simple.yaml)** - Basic HTTP-01 ClusterIssuer
- **[clusterissuer-http01-lb.yaml](./clusterissuer-http01-lb.yaml)** - LoadBalancer HTTP-01 ClusterIssuer
- **[certificate-http01.yaml](./certificate-http01.yaml)** - Sample Certificate resource

### **Application Configurations**
- **[nginx-app-fixed.yaml](./nginx-app-fixed.yaml)** - NGINX deployment with TLS
- **[nginx-tls-config.yaml](./nginx-tls-config.yaml)** - NGINX TLS configuration

### **Troubleshooting and Fixes**
- **[cert-manager-rbac-fix.yaml](./cert-manager-rbac-fix.yaml)** - RBAC permissions fix

---

## 📋 Quick Start Guide

### **Option 1: Complete Learning Path (Recommended)**
```bash
# 1. Read the main guide first
cat cert-management-basics-to-advanced.md

# 2. Follow exercises in order
# Start with: cert-basics.md
# Then: cert-generation-basics.md
# Continue through the sequence...
```

### **Option 2: Jump to Kubernetes Automation**
If you already understand certificate basics:
```bash
# Skip to cert-manager automation
# Read: cert-generation-automatedwithcertmanager.md
# Deploy cert-manager and configure ACME
```

### **Option 3: Advanced End-to-End TLS**
For complex production scenarios:
```bash
# Jump to advanced implementation
# Read: cert-generation-automatedwithcm-e2etls.md
# Implement two-tier CA architecture
```

---

## 🎓 Learning Outcomes

After completing these exercises, you will understand:

### **Fundamental Concepts**
- ✅ X.509 certificate structure and PKI principles
- ✅ Certificate chains and trust relationships
- ✅ TLS handshake process and security properties

### **Practical Skills**
- ✅ Manual certificate generation with OpenSSL
- ✅ Certificate deployment and configuration
- ✅ Troubleshooting certificate issues

### **Automation Expertise**
- ✅ ACME protocol implementation (RFC 8555)
- ✅ cert-manager deployment and configuration
- ✅ Let's Encrypt integration and challenge handling

### **Advanced Implementations**
- ✅ Internal CA deployment and management
- ✅ End-to-end TLS encryption architectures
- ✅ Multi-tier certificate hierarchies

### **Production Readiness**
- ✅ Certificate lifecycle automation
- ✅ Monitoring and alerting strategies
- ✅ Security best practices and compliance considerations

---

## �� Troubleshooting Resources

- **[cert-manager-troubleshooting.md](./cert-manager-troubleshooting.md)** - Common issues and solutions
- **Configuration files** - Ready-to-use YAML examples
- **Error analysis** - Detailed debugging techniques included in main exercises

---

## 🔗 Additional Resources

### **External Documentation**
- [RFC 8555 - ACME Protocol](https://datatracker.ietf.org/doc/html/rfc8555)
- [cert-manager Documentation](https://cert-manager.io/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Kubernetes TLS Documentation](https://kubernetes.io/docs/concepts/services-networking/ingress/#tls)

### **Related Topics**
- Service mesh certificate management (Istio, Linkerd)
- Multi-cloud certificate orchestration
- DevSecOps certificate automation
- Compliance and audit considerations

---

## 📞 Support and Contributing

If you encounter issues or have suggestions for improvements:

1. **Check troubleshooting guide** first
2. **Review error logs** and follow debugging steps in exercises
3. **Test configurations** using provided YAML files
4. **Document solutions** for common issues encountered

---

## 🏗️ Environment Requirements

### **Basic Exercises (cert-basics, cert-generation-basics)**
- Linux environment (Ubuntu 20.04+ recommended)
- OpenSSL toolkit
- Text editor (vim, nano, or VS Code)

### **Kubernetes Exercises (cert-manager, e2etls)**
- Azure Kubernetes Service (AKS) cluster
- kubectl configured with cluster access
- Helm 3.x installed
- Domain name with DNS management capability
- Basic Kubernetes knowledge

### **Network Requirements**
- Internet access for Let's Encrypt ACME challenges
- Port 80 access for HTTP-01 validation
- Port 443 for HTTPS services
- DNS resolution for challenge domains

---

**🎯 Ready to Begin?** Start with [cert-management-basics-to-advanced.md](./cert-management-basics-to-advanced.md) for the complete overview, then follow the numbered exercise sequence for hands-on implementation experience.
