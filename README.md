# Accounts Payable Invoice Extractor (Microsoft Graph)

## Setup
1. Register an Azure AD App with Application permissions:
   - Mail.Read
2. Grant admin consent
3. Copy `.env.example` to `.env` and fill in values

## Install
pip install -r requirements.txt

## Run
python main.py

Attachments will be saved to:
output/invoices/