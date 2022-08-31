# EmeraldEye
Python3 TLS Reverse Shell Implimentation

# Communication Flow
1. server is started - generates its own TLS PEM
2. server waits for incoming connections on "knock" port
3. an agent is started - generates its own TLS PEM
4. agent inits raw socket connection to server on "KNOCK_PORT"
5. server stores connection
6. when user is ready, choose option on server which box to reverse shell to
7. server sends public tls cert over "knock" port to agent
8. agent responds by sending its own public tls cert over "knock" port to server
9. server responds with "go" packet on "knock" port
10. server starts to listen for tls connection on "TLS_PORT"
11. agent inits connection on "TLS_PORT"
12. secure connection now on "TLS_PORT"
13. agent spins up bash subprocess and redirects stdin/err/out to TLS connection
14. server spins up terminal interface for reverse shell
15. user can now execute encrypted commands on remote agent using reverse shell
16. to exit from current machine connection enter "exit"

# Notes
- Agents that lose connection to server will retry every 15 seconds

# Config
In server.py and agent.py; there are global vars called "KNOCK_PORT", "TLS_PORT", these can be any port number as long as they are in parity in both files. "HOST" in agent.py should be set to the local/remote ip of the server. 

# Usage
## Launch Server with:
```python3 server.py```
## Launch Agnet with:
```python3 agent.py```
## Make sure you invoke with correct permissions to open ports
