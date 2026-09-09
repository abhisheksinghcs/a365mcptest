"""Fake in-memory data shared by both server flavours."""
import itertools

KB = [
    {"id": "KB-001", "title": "Reset your Zava VPN profile",
     "body": "If the Zava VPN client fails to connect, remove the profile and re-download it from the IT portal. Restart the client afterwards.",
     "tags": ["vpn", "network", "remote"]},
    {"id": "KB-002", "title": "Requesting a new laptop",
     "body": "Submit a hardware request in the IT portal. Standard refresh cycle is 36 months. Manager approval is required for early refresh.",
     "tags": ["hardware", "laptop", "procurement"]},
    {"id": "KB-003", "title": "Multi-factor authentication setup",
     "body": "Install Microsoft Authenticator and register at aka.ms/mfasetup. Hardware keys (FIDO2) are supported for privileged accounts.",
     "tags": ["mfa", "security", "identity"]},
    {"id": "KB-004", "title": "Expense report deadlines",
     "body": "Expense reports must be filed within 30 days of the transaction date. Late reports require finance director approval.",
     "tags": ["finance", "expenses", "policy"]},
]

TICKETS = {
    "ZAVA-1001": {"title": "VPN drops every 10 minutes", "description": "Client disconnects on home Wi-Fi.",
                  "priority": "High", "status": "In Progress", "owner": "network-team"},
    "ZAVA-1002": {"title": "Need Visio license", "description": "Architecture diagrams for Q4 project.",
                  "priority": "Low", "status": "Open", "owner": "unassigned"},
    "ZAVA-1003": {"title": "MFA prompt loop on new phone", "description": "Authenticator keeps asking to re-register.",
                  "priority": "Medium", "status": "Resolved", "owner": "identity-team"},
}

_counter = itertools.count(1004)


def next_ticket_id() -> str:
    return f"ZAVA-{next(_counter)}"
