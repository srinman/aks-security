# Certificate Basics: Understanding PKI and X.509 Certificates

## Simple Certificate Architecture Overview

Before diving into the details, let's understand the basic concept with just 3 main entities:

```
┌─────────────────────────────────────────────────────────────────┐
│                   SIMPLE CERTIFICATE FLOW                      │
│                                                                 │
│  1️⃣ ENTITY/SUBJECT          2️⃣ CERTIFICATE AUTHORITY (CA)      │
│     (Alice)                      (Trusted Third Party)          │
│                                                                 │
│  🔑 Has Key Pair             🏛️ Validates Identity              │
│  📝 Requests Certificate     🔏 Signs Certificate               │
│  📜 Uses Certificate         📋 Manages Lifecycle               │
│                                                                 │
│     │                              │                           │
│     │ 1. Send Public Key          │                           │
│     │    + Identity Proof         │                           │
│     ├─────────────────────────────▶│                           │
│     │                              │ 2. Verify Identity       │
│     │                              │    Sign Certificate      │
│     │ 3. Receive Signed           │                           │
│     │    Certificate              │                           │
│     │◄─────────────────────────────┤                           │
│     │                              │                           │
│     │                              │                           │
│     │ 4. Present Certificate       │                           │
│     │    to prove identity         │                           │
│     ▼                              │                           │
│                                    │                           │
│  3️⃣ CLIENT/RELYING PARTY          │                           │
│     (Bob's Browser)                 │                           │
│                                    │                           │
│  🔍 Validates Certificate          │                           │
│  ✅ Trusts CA Signature            │                           │
│  🤝 Establishes Secure Connection  │                           │
│                                    │                           │
│     │ 5. Verify Certificate        │                           │
│     │    Signature with CA         │                           │
│     ├─────────────────────────────▶│                           │
│     │ 6. Confirm: "Yes, this      │                           │
│     │    certificate is valid"     │                           │
│     │◄─────────────────────────────┘                           │
│                                                                 │
│  💡 KEY INSIGHT: Client trusts Alice ONLY because              │
│     CA vouches for her identity with a digital signature       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### **The Core Problem Certificates Solve:**

**❌ WITHOUT CERTIFICATES:**
```
Alice: "Hi Bob, here's my public key to encrypt messages to me"
Bob:   "How do I know this is really Alice's key and not an attacker's?"
       "I have NO WAY to verify this!"
```

**✅ WITH CERTIFICATES:**
```
Alice: "Hi Bob, here's my certificate with my public key, signed by CA"
Bob:   "I trust this CA, and CA says this key belongs to Alice"
       "Therefore, I can trust this is really Alice's key!"
```

---

## Table of Contents
1. [Key Players and Entities](#key-players-and-entities)
2. [PKI Architecture Overview](#pki-architecture-overview)
3. [Detailed Role Explanations](#detailed-role-explanations)
4. [X.509 Certificate Standard](#x509-certificate-standard)
5. [Step-by-Step Certificate Process](#step-by-step-certificate-process)
6. [Trust Chain Validation](#trust-chain-validation)
7. [Real-World Examples](#real-world-examples)

---

## Key Players and Entities

In a Public Key Infrastructure (PKI) system, there are three main entities:

### 1. **Certificate Holder (Entity/Subject)**
- **Person or Software Component** that needs to prove their identity
- Examples: Web servers, email users, applications, services, devices
- Possesses a **unique key pair**: Private Key (secret) + Public Key (shareable)
- Uses certificates to prove identity to others

### 2. **Certificate Authority (CA)**
- **Trusted third party** that issues and manages digital certificates
- Verifies the identity of certificate requesters
- Signs certificates with their own private key
- Examples: Let's Encrypt, DigiCert, internal enterprise CAs
- Maintains Certificate Revocation Lists (CRL)

### 3. **Relying Party (Client)**
- **Entities that need to verify** the identity of certificate holders
- Examples: Web browsers, email clients, other services
- **Trust specific CAs** through pre-installed root certificates
- Validate certificates presented by other entities

---

## PKI Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        PKI ECOSYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐          ┌─────────────────┐               │
│  │   ROOT CA       │          │  INTERMEDIATE   │               │
│  │   (Self-Signed) │◄─────────┤      CA         │               │
│  │                 │  trusts  │                 │               │
│  │ 🔐 Root Cert    │          │ 🔐 Int. Cert    │               │
│  └─────────────────┘          └─────────────────┘               │
│           ▲                             │                       │
│           │                             │ issues                │
│           │ pre-installed               ▼                       │
│           │ trust                ┌─────────────────┐            │
│  ┌─────────────────┐             │   END ENTITY    │            │
│  │  RELYING PARTY  │             │   CERTIFICATE   │            │
│  │   (Client)      │             │                 │            │
│  │                 │             │ Subject: Alice  │            │
│  │ 🔍 Validates    │◄────────────┤ Public Key: ... │            │
│  │    Certificates │  presents   │ Issuer: Int. CA │            │
│  │                 │  certificate│ Signature: ...  │            │
│  └─────────────────┘             └─────────────────┘            │
│                                             ▲                   │
│                                             │                   │
│                                    ┌─────────────────┐          │
│                                    │   CERTIFICATE   │          │
│                                    │     HOLDER      │          │
│                                    │    (Alice)      │          │
│                                    │                 │          │
│                                    │ 🔑 Private Key  │          │
│                                    │ 🔓 Public Key   │          │
│                                    └─────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Trust Relationship Flow:
```
Root CA ──trusts──▶ Intermediate CA ──issues──▶ End Entity Certificate
   ▲                                                      │
   │                                                      │
   └──────── pre-installed trust ◄────────────────────────┘
              (in Client/Browser)
```

---

## Detailed Role Explanations

### 1. Certificate Holder (Entity/Subject)

#### **Identity Foundation: Key Pair Generation**
```
┌─────────────────────────────────────────────────────────────┐
│                  KEY PAIR GENERATION                        │
│                                                             │
│  ┌─────────────────┐    Mathematical    ┌─────────────────┐ │
│  │   PRIVATE KEY   │◄─── Relationship ──►│   PUBLIC KEY    │ │
│  │                 │                     │                 │ │
│  │ 🔐 Keep Secret  │                     │ 🔓 Share Freely │ │
│  │                 │                     │                 │ │
│  │ • Signs data    │                     │ • Verifies sig. │ │
│  │ • Decrypts data │                     │ • Encrypts data │ │
│  │ • Never shared  │                     │ • Published     │ │
│  └─────────────────┘                     └─────────────────┘ │
│                                                             │
│  Example RSA Key Generation:                                │
│  openssl genrsa -out private.key 2048                       │
│  openssl rsa -in private.key -pubout -out public.key        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **What the Certificate Holder Does:**
1. **Generates a unique key pair** (private/public keys)
2. **Keeps private key secret** - never shares it
3. **Submits public key to CA** for certification
4. **Proves identity to CA** through various validation methods
5. **Receives signed certificate** from CA
6. **Uses certificate** to prove identity to others
7. **Protects private key** from compromise

### 2. Certificate Authority (CA)

#### **CA's Core Functions:**
```
┌─────────────────────────────────────────────────────────────┐
│                   CERTIFICATE AUTHORITY                     │
│                                                             │
│  1. IDENTITY VERIFICATION                                   │
│     ┌─────────────────┐                                    │
│     │ Domain Control  │ ← HTTP-01, DNS-01 challenges       │
│     │ Email Control   │ ← Email verification               │
│     │ Organization    │ ← Legal documentation             │
│     │ Extended Valid. │ ← In-person verification          │
│     └─────────────────┘                                    │
│                                                             │
│  2. CERTIFICATE ISSUANCE                                    │
│     ┌─────────────────┐                                    │
│     │ Public Key +    │                                    │
│     │ Identity Info   │ ──CA Signs──▶ X.509 Certificate   │
│     │ + CA Signature  │               (Trusted Document)   │
│     └─────────────────┘                                    │
│                                                             │
│  3. LIFECYCLE MANAGEMENT                                    │
│     • Certificate Renewal                                   │
│     • Certificate Revocation (CRL/OCSP)                    │
│     • Key Escrow (optional)                                │
│     • Audit and Compliance                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### **CA Validation Levels:**
- **Domain Validation (DV)**: Proves control over domain name
- **Organization Validation (OV)**: Verifies organization details
- **Extended Validation (EV)**: Highest level, legal entity verification

### 3. Relying Party (Client)

#### **Trust Store and Validation:**
```
┌─────────────────────────────────────────────────────────────┐
│                    RELYING PARTY (CLIENT)                   │
│                                                             │
│  ┌─────────────────┐        ┌─────────────────┐            │
│  │   TRUST STORE   │        │   CERTIFICATE   │            │
│  │                 │        │   VALIDATION    │            │
│  │ 🏛️ Root CA Certs│        │                 │            │
│  │ 🏛️ Mozilla NSS  │        │ ✅ Signature    │            │
│  │ 🏛️ Windows Store│────────▶│ ✅ Expiration   │            │
│  │ 🏛️ macOS Keychain│       │ ✅ Chain of     │            │
│  │ 🏛️ Custom Certs │        │    Trust        │            │
│  └─────────────────┘        │ ✅ Revocation   │            │
│                              │ ✅ Hostname     │            │
│                              └─────────────────┘            │
│                                                             │
│  CLIENT CANNOT TRUST:                                       │
│  ❌ Raw public keys (no CA signature)                      │
│  ❌ Self-signed certificates (unless explicitly added)      │
│  ❌ Certificates from untrusted CAs                        │
│  ❌ Expired or revoked certificates                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## X.509 Certificate Standard

### **What is an X.509 Certificate?**

An **X.509 certificate** is a digital document that binds a public key to an identity, signed by a trusted Certificate Authority. It's the standard format used in PKI systems worldwide.

### **Certificate Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│                    X.509 CERTIFICATE                        │
├─────────────────────────────────────────────────────────────┤
│  HEADER                                                     │
│  -----BEGIN CERTIFICATE-----                               │
│                                                             │
│  📋 CERTIFICATE DATA (TBSCertificate):                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Version: v3                                       │   │
│  │ • Serial Number: 03:5F:A0:8B:7C:3D...             │   │
│  │ • Signature Algorithm: sha256WithRSAEncryption     │   │
│  │ • Issuer: CN=Let's Encrypt Authority X3           │   │
│  │ • Validity:                                        │   │
│  │   - Not Before: 2023-01-15 10:30:00 UTC          │   │
│  │   - Not After:  2023-04-15 10:30:00 UTC          │   │
│  │ • Subject: CN=example.com                         │   │
│  │ • Subject Public Key Info:                        │   │
│  │   - Algorithm: RSA 2048-bit                       │   │
│  │   - Public Key: MIIBIjANBgkqhkiG9w0B...         │   │
│  │ • Extensions:                                      │   │
│  │   - Subject Alt Names: example.com, www.ex...     │   │
│  │   - Key Usage: Digital Signature, Key Encip...    │   │
│  │   - Extended Key Usage: Server Authentication     │   │
│  │   - Authority Key Identifier: keyid:A8:4A:6A...   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🔏 CA SIGNATURE:                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Signature Algorithm: sha256WithRSAEncryption        │   │
│  │ Signature Value:                                    │   │
│  │     5C:E8:7B:A1:2F:4D:C9:8A:B2:3F:1E:9D:C4:...   │   │
│  │     [This is the CA's digital signature of the     │   │
│  │      certificate data above, proving authenticity] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  FOOTER                                                     │
│  -----END CERTIFICATE-----                                 │
└─────────────────────────────────────────────────────────────┘
```

### **Critical Certificate Components:**

1. **Subject**: Who owns this certificate (CN=example.com)
2. **Issuer**: Which CA signed this certificate
3. **Public Key**: The actual public key being certified
4. **Validity Period**: When certificate is valid (Not Before/After)
5. **Digital Signature**: CA's signature proving authenticity
6. **Extensions**: Additional information (SAN, Key Usage, etc.)

---

## Step-by-Step Certificate Process

### **Phase 1: Key Generation and Certificate Request**

```
┌─────────────────────────────────────────────────────────────┐
│                    STEP 1-3: PREPARATION                    │
│                                                             │
│  👤 Certificate Holder (Alice)                             │
│                                                             │
│  1️⃣ GENERATE KEY PAIR                                      │
│     ┌─────────────────┐    ┌─────────────────┐             │
│     │   Private Key   │    │   Public Key    │             │
│     │  🔐 (Secret)    │    │  🔓 (Shareable) │             │
│     └─────────────────┘    └─────────────────┘             │
│                                     │                       │
│  2️⃣ CREATE CSR (Certificate Signing Request)              │
│     ┌─────────────────────────────────────────┐             │
│     │ CSR Contains:                           │             │
│     │ • Subject: CN=alice.example.com        │             │
│     │ • Public Key: [Alice's public key]     │             │
│     │ • Extensions: DNS names, key usage     │             │
│     │ • Signature: [Signed with private key] │             │
│     └─────────────────────────────────────────┘             │
│                                     │                       │
│  3️⃣ SUBMIT TO CA                   ▼                      │
│     ┌─────────────────────────────────────────┐             │
│     │          Submit CSR to CA               │             │
│     │     + Proof of Identity/Control         │             │
│     └─────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Phase 2: CA Validation and Certificate Issuance**

```
┌─────────────────────────────────────────────────────────────┐
│                   STEP 4-6: CA PROCESSING                   │
│                                                             │
│  🏛️ Certificate Authority (CA)                              │
│                                                             │
│  4️⃣ IDENTITY VALIDATION                                    │
│     ┌─────────────────────────────────────────┐             │
│     │ For alice.example.com:                  │             │
│     │ • HTTP-01: Place file on web server    │             │
│     │ • DNS-01: Add TXT record to DNS        │             │
│     │ • Email: Send verification email       │             │
│     │ ✅ Domain control confirmed            │             │
│     └─────────────────────────────────────────┘             │
│                                     │                       │
│  5️⃣ CERTIFICATE CREATION            ▼                      │
│     ┌─────────────────────────────────────────┐             │
│     │ Build X.509 Certificate:                │             │
│     │ • Copy CSR public key & subject info   │             │
│     │ • Add CA as Issuer                     │             │
│     │ • Set validity period (90 days)        │             │
│     │ • Add serial number & extensions       │             │
│     └─────────────────────────────────────────┘             │
│                                     │                       │
│  6️⃣ DIGITAL SIGNING                 ▼                      │
│     ┌─────────────────────────────────────────┐             │
│     │  CA signs certificate with:             │             │
│     │  🔐 CA's Private Key                   │             │
│     │  📜 SHA-256 hash algorithm             │             │
│     │  ✅ Creates unforgeable signature      │             │
│     └─────────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Phase 3: Certificate Deployment and Usage**

```
┌─────────────────────────────────────────────────────────────┐
│                 STEP 7-9: CERTIFICATE USAGE                 │
│                                                             │
│  7️⃣ CERTIFICATE DELIVERY                                   │
│     🏛️ CA ──────▶ 👤 Alice                                │
│     📜 Signed X.509 Certificate                            │
│                                                             │
│  8️⃣ CERTIFICATE INSTALLATION                               │
│     👤 Alice installs certificate on her web server        │
│     ┌─────────────────────────────────────────┐             │
│     │ Web Server Configuration:               │             │
│     │ • Certificate file: alice.crt           │             │
│     │ • Private key file: alice.key          │             │
│     │ • Certificate chain: intermediate.crt  │             │
│     └─────────────────────────────────────────┘             │
│                                                             │
│  9️⃣ CLIENT CONNECTION                                      │
│     🌐 Browser ◄──────── 👤 Alice's Server                │
│         │                      │                           │
│         │    ← Presents Cert ←  │                           │
│         │    → Validates Cert → │                           │
│         │    ← Establishes TLS ← │                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Trust Chain Validation

### **Why Clients Can't Trust Raw Public Keys**

**❌ WITHOUT CERTIFICATES:**
```
👤 Alice: "Here's my public key: [key data]"
🌐 Client: "How do I know this is really Alice's key?"
           "Could be an attacker's key!"
           "NO WAY TO VERIFY!"
```

**✅ WITH CERTIFICATES:**
```
👤 Alice: "Here's my certificate signed by Trusted CA"
🌐 Client: "I trust that CA, so if CA says this is Alice's key, I believe it"
           "CA has verified Alice's identity"
           "CERTIFICATE ESTABLISHES TRUST!"
```

### **Certificate Chain Validation Process:**

```
┌─────────────────────────────────────────────────────────────┐
│                 CERTIFICATE CHAIN VALIDATION                │
│                                                             │
│  🌐 CLIENT RECEIVES CERTIFICATE CHAIN:                     │
│                                                             │
│  📜 [End Entity Certificate]                               │
│      ├─ Subject: CN=alice.example.com                      │
│      ├─ Issuer: CN=Intermediate CA                         │
│      └─ Signature: [Signed by Intermediate CA]             │
│                    │                                       │
│                    ▼                                       │
│  📜 [Intermediate Certificate]                             │
│      ├─ Subject: CN=Intermediate CA                        │
│      ├─ Issuer: CN=Root CA                                │
│      └─ Signature: [Signed by Root CA]                     │
│                    │                                       │
│                    ▼                                       │
│  📜 [Root Certificate] ← Pre-installed in client trust store│
│      ├─ Subject: CN=Root CA                                │
│      ├─ Issuer: CN=Root CA (self-signed)                  │
│      └─ Signature: [Self-signed]                           │
│                                                             │
│  🔍 VALIDATION STEPS:                                      │
│  1️⃣ Check End Entity signature using Intermediate CA key  │
│  2️⃣ Check Intermediate signature using Root CA key        │
│  3️⃣ Verify Root CA is in trusted store                   │
│  4️⃣ Verify all certificates are within validity period    │
│  5️⃣ Check certificate hasn't been revoked (CRL/OCSP)     │
│  6️⃣ Verify hostname matches certificate Subject/SAN       │
│                                                             │
│  ✅ IF ALL CHECKS PASS: Certificate chain is TRUSTED      │
│  ❌ IF ANY CHECK FAILS: Connection is REJECTED            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Trust Store Examples:**

```bash
# Linux (Ubuntu/Debian)
/etc/ssl/certs/ca-certificates.crt

# Linux (CentOS/RHEL)
/etc/pki/tls/certs/ca-bundle.crt

# Windows
certlm.msc → Trusted Root Certification Authorities

# macOS
/System/Library/Keychains/SystemRootCertificates.keychain

# Mozilla Firefox
Security → Certificates → View Certificates → Authorities

# Google Chrome (uses system store)
Settings → Privacy and Security → Security → Manage Certificates
```

---

## Real-World Examples

### **Example 1: HTTPS Website Certificate**

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTPS CERTIFICATE EXAMPLE                │
│                                                             │
│  🌐 User visits: https://github.com                        │
│                                                             │
│  📜 GitHub's Certificate:                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Subject: CN=github.com                              │   │
│  │ Issuer: CN=DigiCert TLS Hybrid ECC SHA384 2020 CA1 │   │
│  │ SAN: github.com, www.github.com                    │   │
│  │ Valid: 2023-02-07 to 2024-03-07                    │   │
│  │ Public Key: P-256 ECDSA                            │   │
│  │ Key Usage: Digital Signature, Key Agreement        │   │
│  │ EKU: Server Authentication                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  🔐 Trust Chain:                                           │
│  GitHub Cert ←── DigiCert Intermediate ←── DigiCert Root   │
│                                              (in browser)   │
│                                                             │
│  ✅ Browser validates and shows 🔒 secure connection      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Example 2: Email Certificate (S/MIME)**

```
┌─────────────────────────────────────────────────────────────┐
│                   EMAIL CERTIFICATE EXAMPLE                 │
│                                                             │
│  📧 Alice wants to send signed/encrypted email              │
│                                                             │
│  📜 Alice's S/MIME Certificate:                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Subject: CN=Alice Smith, E=alice@company.com       │   │
│  │ Issuer: CN=Company Internal CA                     │   │
│  │ Email: alice@company.com                           │   │
│  │ Key Usage: Digital Signature, Key Encipherment     │   │
│  │ EKU: Email Protection                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  📬 Email Process:                                         │
│  1. Alice signs email with private key                    │
│  2. Alice encrypts email with recipient's public key      │
│  3. Recipient validates signature using Alice's cert      │
│  4. Recipient decrypts email with their private key       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### **Example 3: Code Signing Certificate**

```
┌─────────────────────────────────────────────────────────────┐
│                CODE SIGNING CERTIFICATE EXAMPLE             │
│                                                             │
│  💻 Software Developer needs to sign application            │
│                                                             │
│  📜 Code Signing Certificate:                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Subject: CN=ACME Software Inc                       │   │
│  │ Issuer: CN=DigiCert Assured ID Code Signing CA     │   │
│  │ Organization: ACME Software Inc                     │   │
│  │ Key Usage: Digital Signature                       │   │
│  │ EKU: Code Signing                                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💾 Signing Process:                                       │
│  1. Developer signs .exe/.msi with private key            │
│  2. Certificate embedded in signed file                   │
│  3. Windows validates signature before execution          │
│  4. User sees "Verified publisher: ACME Software Inc"     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

### **🎯 Core Concepts:**

1. **Certificates bind public keys to identities** - this is their fundamental purpose
2. **Only CA-signed certificates are trusted** - clients reject raw public keys
3. **Trust flows from Root CAs** - pre-installed in operating systems and browsers
4. **Certificate chains establish transitive trust** - Root → Intermediate → End Entity
5. **Multiple validation checks ensure security** - signature, expiration, revocation, hostname

### **🔐 Security Principles:**

- **Private keys must never be shared** - compromise means identity theft
- **Certificates don't contain private keys** - only public keys and identity info
- **CA signatures prevent forgery** - mathematically impossible to fake without CA's private key
- **Trust stores are critical** - define which CAs are trusted
- **Certificate lifecycle matters** - renewal, revocation, and expiration handling

### **💡 Why This Matters:**

Without certificates, secure communication would be impossible because:
- No way to verify public key ownership
- Susceptible to man-in-the-middle attacks
- No mechanism for identity verification
- No framework for trust establishment

Certificates solve the **key distribution problem** and enable secure communications at internet scale.

---

## Practical Commands for Exploring Certificates

```bash
# View a website's certificate
openssl s_client -connect github.com:443 -servername github.com | openssl x509 -noout -text

# Generate a private key
openssl genrsa -out private.key 2048

# Generate a Certificate Signing Request (CSR)
openssl req -new -key private.key -out request.csr

# View CSR contents
openssl req -in request.csr -noout -text

# View certificate file
openssl x509 -in certificate.crt -noout -text

# Check certificate chain
openssl verify -verbose -CAfile ca-bundle.crt certificate.crt

# View system trust store (Linux)
ls -la /etc/ssl/certs/
```

This foundation will help trainees understand how certificates work in real-world scenarios like Kubernetes, web servers, and enterprise PKI systems.
