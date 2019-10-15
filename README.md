# Requirement
```
pip install docker
```
# Env Config
config.json
```
{
    "node":3,
    "manager":3,
    "worker":0,
    "container":{
      "api":{
        "exec_cmd":"ls -ltr"
      },
      "dashboard":{
          "exec_cmd":"pwd"
      }
    },
    "service":{
        "helloworld":{
            "replicas":3
        }
    },
    "hostname":"192.168.4.225",
    "port":"2376",
    "container_check":1,
    "service_check":1,
    "custom_command_run":1,
    "mail":{
        "notification":1,
        "sender_email":"mail@domain.in",
        "receivers_email":["mail1@domain.in", "mail2@domain.in"],
        "sender_password":"mailpassword",
        "smtp_host":"smtp.gmail.com",
        "smtp_port":587
    },
    "logging":{
        "enable":1,
        "type":"console",
        "file_name":"doc_monitor"
    }
}
```
### - node
```
count of node to be connected.
```

### - manager
```
count of required manager node.
```
### - worker
```
count of required worker node.
```
### - service
```
Give the service name ["helloworld"] and the replicas ["3"].
```
### - hostname
```
Docker leader node IP  
```
### - port
```
Docker daemon mode PORT
```
### - container
```
Give the container name ["site_api"] and the command which is going to be run inside the container ["exec_cmd":"ls -ltr"].
```
### - container_check
```
Enable / disable the monitoring container information 1/0
```
### - service_check
```
Enable / disable the monitoring service information 1/0
```
### - custom_command_run
```
Enable / disable to execute custom command into the particular container
```
### - mail
```
- notification : Enable / disable to send mail alert
- sender_email : Sender email address
- receivers_email : Receiver email's with comma seperated value
- sender_password : Sender password
- smtp_host : Email server smtp host
- smtp_port : Email server port
```
### - logging
```
- enable : Enable/disable logging 1/0
- type : Logging type console/file/stream [default : stream]
- file_name : log file name
```


# Validation alert message 
###### #TODO need more validation

### - node mismatch 
Please check connected node's. Some node's are missing!
### - node matched!
All node's are connected.
### - node availability success
All node's are active.
### - node availability drain
Some node's are drained, please make it active. DRAIN node(s) {count}

### - node status check success
All node's are ready!
### - node status check fail
Some node's are down, please make it ready. DOWN node(s) {count}

### - manager matched!
All manager node's are running successfully.
### - manager mismatch
Some manager node's are missing!.

### - worker matched!
All worker node's are running successfully.
### - worker mismatch
Some worker node's are missing!.


### - Service replicas mismatch
{service_name} : need {count} more replicas.
### - Service replicas matched
{service_name} : Replicas mached!
### - Service down
{service_name} : Service down!

# Run
```
python monitor.py
```
