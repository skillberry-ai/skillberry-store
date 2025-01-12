# Simple usage of the IBM rits inference service

## How to run

1. Define the `RITS_API_KEY` environment variable
```bash
export RITS_API_KEY=********************************
```

- IBM Researchers need to log-in to obtain their api-key in order to access RITS hosted models. 
Navigate to: https://rits.fmaas.res.ibm.com/#


- Currently, users need to either be on an IBM campus network, or utilize 
the `tunnelall` IBM VPN profile to access the RITS UI and models

- >Note: For emea, use in the Cisco VPN: http://sasvpn-fast.emea.ibm.com/TUNNELALL

2. Execute the code

```bash
python main.py
```