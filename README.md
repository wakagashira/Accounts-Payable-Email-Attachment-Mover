Accounts Payable Email Attachment Mover
Overview

This project is a Python-based automation that connects to a Microsoft 365 mailbox and extracts invoice attachments in a transparent, non-disruptive way.

It is designed for shared Accounts Payable mailboxes where:

multiple people or systems use the inbox

emails must not be moved, deleted, or altered

processing must be idempotent and auditable

The script reads inbound emails from the Inbox only, downloads qualifying attachments, and tracks what has already been processed using SQL Server.

What the project does

When executed, the script:

Authenticates to Microsoft Graph using Application permissions

Connects to one specific mailbox (restricted via Exchange Application Access Policy)

Reads messages from the Inbox only

Filters for emails that:

have attachments

appear to be invoices based on subject keywords

Downloads allowed attachment types to a local folder

Records processed emails in SQL Server to prevent reprocessing

Applies an Outlook category (RaivenSynced) for human visibility

Exits

The script is safe to run repeatedly.

What the project does NOT do

Does not move emails

Does not delete emails

Does not mark emails as read/unread

Does not modify email content

Does not send emails

Does not scan folders outside the Inbox

Does not parse invoice data (OCR, totals, etc.)

Mailbox state remains intact and usable by other users and processes.

Architecture summary

Mailbox access

Microsoft Graph

Application permissions

Restricted to a single mailbox via Exchange Application Access Policy

Idempotency

SQL Server is the source of truth

Each processed email Message ID is stored

Emails already recorded are skipped on future runs

Transparency

Outlook category RaivenSynced is applied to processed emails

Inbox contents remain unchanged

Storage

Attachments are saved to a local directory on disk

SQL Server stores processing metadata

Configuration

Configuration is provided via a .env file.

Required values
TENANT_ID=...
CLIENT_ID=...
CLIENT_SECRET=...
MAILBOX=invoices@company.com

SQL_SERVER=...
SQL_DATABASE=...
SQL_TRUSTED_CONNECTION=true


(SQL authentication is also supported if required.)

Permissions required

Microsoft Graph (Application permissions):

Mail.ReadWrite

Admin consent is required.

Exchange Online:

Application Access Policy restricting the app to a single mailbox

Output

Attachments are saved locally to:

output/invoices/


The folder is created automatically if it does not exist.

Tracking and auditing

SQL Server tracks which emails have been processed

Outlook category provides mailbox-level visibility

No reliance on read/unread state

No hidden mailbox rules

This design supports audits, troubleshooting, and replay scenarios.

Typical use cases

Ingesting vendor invoices from a shared AP mailbox

Feeding downstream AP or ERP workflows

Running on a schedule (Task Scheduler, cron, etc.)

Operating safely alongside human users

Extensibility

The project is designed to be extended without changing its core behavior. Common additions include:

Attachment hashing for duplicate invoice detection

Vendor identification

OCR and invoice field extraction

Reporting and reconciliation

Centralized logging

Security posture

Least-privilege access

Single-tenant application

Single-mailbox restriction

No destructive mailbox operations

Credentials managed via environment variables

Summary

This project provides a safe, repeatable, and transparent way to extract invoice attachments from a Microsoft 365 mailbox without interfering with normal email usage.

It is intended to be reliable, auditable, and easy to operate in real-world Accounts Payable environments.