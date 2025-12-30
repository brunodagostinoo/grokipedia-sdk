# Security Policy

## Supported Versions

We take security seriously and are committed to addressing security vulnerabilities in our software. Since grokipedia-sdk is currently in alpha development (v0.x), we provide security updates for **all currently supported versions**.

| Version | Supported          |
| ------- | ------------------ |
| 0.x.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

**Note:** Once grokipedia-sdk reaches version 1.0.0, we will follow semantic versioning for security support:
- The latest major version will receive security updates
- The previous major version may receive critical security updates for a limited time
- Versions older than that will no longer receive security updates

## Reporting a Vulnerability

If you discover a security vulnerability in grokipedia-sdk, we appreciate your help in disclosing it responsibly. Please **do not** report security vulnerabilities through public GitHub issues, discussions, or pull requests.

### How to Report

**Please report security vulnerabilities by:**
- Creating a **private security advisory** through [GitHub Security Advisories](https://github.com/brunodagostinoo/grokipedia-sdk/security/advisories/new)

### What to Include

When reporting a security vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: Potential impact and severity assessment
3. **Steps to Reproduce**: Detailed steps to reproduce the issue
4. **Affected Versions**: Which versions are affected
5. **Proof of Concept**: If available, a proof-of-concept demonstrating the vulnerability
6. **Your Contact Information**: How we can reach you for follow-up questions

### Our Response Process

1. **Acknowledgment**: We will acknowledge receipt of your report within **48 hours**
2. **Investigation**: We will investigate the issue and provide an initial assessment within **7 days**
3. **Updates**: We will provide regular updates (at least weekly) on our progress
4. **Fix Development**: Once confirmed, we will develop and test a fix
5. **Disclosure**: We will coordinate public disclosure with you after the fix is ready

### Vulnerability Classification

We use the following severity levels based on CVSS v3.1:

- **Critical**: CVSS 9.0-10.0 - Immediate threat to data confidentiality, integrity, or availability
- **High**: CVSS 7.0-8.9 - Significant impact with potential for exploitation
- **Medium**: CVSS 4.0-6.9 - Moderate impact or requires specific conditions
- **Low**: CVSS 0.1-3.9 - Minimal impact or difficult to exploit

### Recognition

We appreciate security researchers who help keep our users safe. With your permission, we will:
- Acknowledge you in the security advisory
- Add you to our Hall of Fame (if you wish)
- Consider you for bounties (if we establish a bug bounty program)

### Disclosure Policy

- We follow responsible disclosure practices
- We will not disclose vulnerability details until a fix is available
- We coordinate disclosure timing with the reporter
- We may request an embargo period for critical vulnerabilities

## Contact

For security-related questions or concerns:
- GitHub Security Advisories: https://github.com/brunodagostinoo/grokipedia-sdk/security/advisories

Thank you for helping keep grokipedia-sdk and its users secure!
