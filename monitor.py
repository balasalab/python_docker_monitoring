import ast
import json
import docker
import smtplib
import logging
from stats import Stats
from settings import CONFIG
import datetime, sys

class bcolors:
    HEADER = ''
    OKBLUE = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''
    UNDERLINE = ''
    CYAN = ''
    MAGENTA = ''
    GREY = ''
    if CONFIG['logging'].get('type')=='console':
    	HEADER = '\033[95m'
    	OKBLUE = '\033[94m'
    	OKGREEN = '\033[92m'
    	WARNING = '\033[93m'
    	FAIL = '\033[91m'
    	ENDC = '\033[0m'
    	BOLD = '\033[1m'
    	UNDERLINE = '\033[4m'
    	CYAN = '\033[96m'
    	MAGENTA = '\033[95m'
    	GREY = '\033[90m'

class Monitor():
	nodes=None
	smtpObj=None
	errors=[]
	def __init__(self):
		if CONFIG['logging'].get('type')=='file':
			logging.basicConfig(filename=CONFIG['logging'].get('file_name')+"_"+str(datetime.date.today())+".log", level=logging.INFO)
		elif CONFIG['logging'].get('type')=='console':
			logging.basicConfig(level=logging.INFO)
		else:
			logging.basicConfig(level=logging.INFO, stream=sys.stdout)

		client=self.connect_client(CONFIG['hostname'])
		self.nodes=client.nodes.list(filters={'role': 'manager'})
		
		self.smtpObj = smtplib.SMTP(CONFIG['mail']['smtp_host'], CONFIG['mail']['smtp_port'])
		self.smtpObj.starttls()
		self.smtpObj.login(CONFIG['mail']['sender_email'], CONFIG['mail']['sender_password'])


	def __del__(self):
		pass

	def send_email(self):
		if self.errors and CONFIG['mail']['notification']:
			msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n"% (CONFIG['mail']['sender_email'], CONFIG['mail']['receivers_email'], CONFIG['mail']['email_subject']))
			for em in self.errors:
				msg+=str(em)+"\r\n\r\n"
			self.smtpObj.sendmail(CONFIG['mail']['sender_email'], CONFIG['mail']['receivers_email'], msg)
			self.smtpObj.quit()
			logging.info("Mail sent ************************************")

	def connect_client(self, ip=None):
		if ip:
			client=docker.DockerClient(base_url=ip+':'+CONFIG['port'])
		else:
			client = docker.from_env()
		return client

	def get_node_count(self):
		return len(self.nodes)

	def scan_nodes(self):
		self.parse_node_data(self.nodes)
		self.send_email()

	def check_node_count(self,node_count):
		if (CONFIG['node']<node_count):
			alert_message="Please check connected node's. Extra "+ str(node_count-CONFIG['node'])+" node connected."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+  bcolors.ENDC)
		elif (CONFIG['node']>node_count):
			alert_message="Please check connected node's. Need "+ str(CONFIG['node']-node_count)+" more node to be connect."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		else:
			logging.info(bcolors.OKGREEN+"All "+str(node_count)+" node's are connected."+bcolors.ENDC)

	def check_node_roles(self,roles):
		if CONFIG['manager'] < roles['manager']:
			alert_message="Manager node exceeds the limit, which is defined in the config."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		elif CONFIG['manager'] > roles['manager']:
			alert_message=str(CONFIG['manager']-roles['manager'])+" more manager node, it's not meet the requirement, which is defined in the config."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+"Need "+alert_message+bcolors.ENDC)
		else:
			logging.info(bcolors.OKGREEN+"All "+str(roles['manager'])+" manager node's are running successfully."+bcolors.ENDC)

		if roles.get('worker', None) and CONFIG['worker'] < roles['worker']:
			alert_message="Worker's node exceeds the limit, which is defined in the config."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		elif roles.get('worker', None) and CONFIG['worker'] > roles['worker']:
			alert_message="Need "+str(CONFIG['worker']-roles['worker'])+" more worker node, it's not meet the requirement, which is defined in the config."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		elif roles.get('worker', None) and roles['worker']==CONFIG['worker']:
			logging.info(bcolors.OKGREEN+"All "+str(roles['worker'])+" worker node's are running successfully."+bcolors.ENDC)
		elif CONFIG['worker']:
			alert_message="Some worker node's are missing!."
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)

	def check_node_availability(self,availdata, node_count):
		if availdata['active']==node_count:
			logging.info(bcolors.OKGREEN+"All "+str(node_count)+" node's are active!"+bcolors.ENDC)
		if 'drain' in availdata:
			alert_message="Some node's are drained, please make it active. DRAIN node(s) : "+ str(availdata['drain'])
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		if 'down' in availdata:
			alert_message="Some node's are down, please make it UP. DOWN node(s) : "+ str(availdata['drain'])
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)

	def check_node_status(self,statusdata, node_count):
		if statusdata['ready']==node_count:
			logging.info(bcolors.OKGREEN+"All "+str(node_count)+" node's are ready state!"+bcolors.ENDC)
		if 'down' in statusdata:
			alert_message="Some node's are down, please make it ready. DOWN node(s) : "+ str(statusdata['down'])
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)

	def parse_node_data(self, data):
		response={}
		response['node_count']=len(data)
		response['node_data']=[]

		leader_count=0
		avail={}
		reach={}
		rolec={}
		status={}

		for k,node in enumerate(data):
			node = node.attrs
			tmp={}
			tmp['node_id']=str(node['ID'])
			# tmp['hostname']=str(node['Status']['Addr'])
			tmp['hostname']=str(node['ManagerStatus']['Addr']).split(':')[0]
			tmp['status']=str(node['Status']['State'])
			if tmp['status'] in status:
				status[tmp['status']]+=1
			else:
				status[tmp['status']]=1
			
			tmp['role']=str(node['Spec']['Role'])
			if tmp['role'] in rolec:
				rolec[tmp['role']]+=1
			else:
				rolec[tmp['role']]=1

			tmp['availability']=str(node['Spec']['Availability'])
			if tmp['availability'] in avail:
				avail[tmp['availability']]+=1
			else:
				avail[tmp['availability']]=1

			if 'ManagerStatus' in node:
				tmp['reachability']=str(node['ManagerStatus']['Reachability'])
				if tmp['reachability'] in reach:
					reach[tmp['reachability']]+=1
				else:
					reach[tmp['reachability']]=1
				tmp['leader']=(node['ManagerStatus'].get('Leader', None))
				leader_count+= 1 if tmp['leader'] else 0

			response['node_data'].append(tmp)
			logging.info(bcolors.WARNING+"-----Node "+str(k)+"-----------------------------------")
			logging.info("Node " +str(k)+" : "+str(tmp['hostname'])+" | "+str(tmp['role'])+" | "+str(tmp['availability']) +" | "+str(tmp['status']) +str(" | Leader " if tmp.get('leader', None) else ""))
			logging.info("-"*50+bcolors.ENDC)

			client=self.connect_client(tmp['hostname'])

			if tmp['status']=='ready' and tmp['role']=='manager':
				vol_data=client.volumes.list()
				volnames=self.get_all_volume_names(vol_data)
			else:
				volnames=[]

			if tmp.get('leader', 0) and CONFIG['service_check']:
				netw_data=data=client.networks.list()
				nids=self.get_all_network_ids(netw_data)

				serv_data=client.services.list()
				self.parse_service_data(serv_data, nids)

			if tmp['status']=='ready' and CONFIG['container_check']:
				con_data=client.containers.list()
				self.parse_container_data(con_data, volnames)
			
		logging.info(bcolors.OKBLUE+"-"*50+bcolors.ENDC)
		
		logging.info(bcolors.OKBLUE+"-----Node stats--------------------------------")
		logging.info("Total connecting nodes : "+str(response['node_count']))
		logging.info("Leader : "+str(leader_count))
		logging.info("Role : "+str(rolec))
		logging.info("Availability : "+str(avail))
		logging.info("Status : "+str(status))
		logging.info("Reachability : "+str(reach))
		logging.info("-"*50+bcolors.ENDC)
		self.check_node_count(response['node_count'])
		self.check_node_roles(rolec)
		self.check_node_availability(avail, response['node_count'])
		self.check_node_status(status, response['node_count'])

	def parse_container_data(self, condata, volumes):
		container_count = len(condata)
		vol_container_count = 0
		data={}
		data['no_of_containers']=container_count
		logging.info(bcolors.CYAN+"-----Total running containers : "+str(container_count)+"----------------------"+bcolors.ENDC)
		data['containers']=[]
		for k,con in enumerate(condata):
			co=con.attrs
			logging.info(bcolors.CYAN+"-----Container "+str(k+1)+"------------------------------"+bcolors.ENDC)
			temp={}
			temp['id']=co['Id']
			temp['image']=co['Image']
			temp['status']=con.status
			temp['name']=con.name
			temp['volume']=[]

			logging.info("Id : "+str(temp['id']))

			if "Labels" in co:
				if 'com.docker.swarm.service.name' in co['Labels']:
					temp['service_name']=co['Labels']['com.docker.swarm.service.name']
					temp['service_id']=co['Labels']['com.docker.swarm.service.id']
					temp['node_id']=co['Labels']['com.docker.swarm.node.id']

			#check and get volumes start
			volume_check=self.check_container_volumes(co, volumes, vol_container_count)
			temp['volume']=volume_check['volume']
			vol_container_count=volume_check['container_with_volume']
			#check and get volumes end

			# get container status start
			self.get_container_stats(con, temp)
			# get container status end

			if temp.get('mem_usage_per', 0) >= 90:
				alert_message=str(temp['name'])+" : Container memory consumed more than 90%. Used : '"+str(temp.get('mem_usage_per', 0))+"%'"
				self.errors.append(alert_message)
				logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)

			data['containers'].append(temp)
			logging.info("Name : "+str(temp['name']))
			logging.info("Status : "+str(temp['status']))
			logging.info("Mem. Usage : "+str(temp.get('mem_usage', 0))+" bytes")
			logging.info("Mem. limit : "+str(temp.get('mem_limit', 0))+" bytes")
			logging.info("Mem. Usage Per. : "+str(temp.get('mem_usage_per', 0)))
			logging.info("CPU Usage : "+str(temp.get('cpu_total_usage', 0)))
			logging.info("Image : "+str(temp['image']))

			# run custom command start
			if CONFIG['custom_command_run']:
				self.custom_command_run(str(temp['name']), con)
			# run custom command end

			logging.info(bcolors.CYAN+"-"*50+bcolors.ENDC)

		# logging.info(json.dumps(data))
		logging.info(bcolors.CYAN+str(vol_container_count)+" volumes attached to containers."+bcolors.ENDC)
		return data

	def custom_command_run(self, con_name, con_obj):
		name=con_name.split(".")[0]
		container_config = CONFIG['container']
		if name in container_config:
			logging.info("*"*100)
			cmd_result=con_obj.exec_run(container_config[name]['exec_cmd'])
			logging.info(cmd_result[1])
			logging.info("*"*100)


	def check_container_volumes(self, data, volumes, vol_container_count):
		resp={}
		resp['volume']=[]
		if 'Mounts' in data:
			for mount in data['Mounts']:
				if mount['Type']=='volume':
					vol_container_count+=1
					volu=str(mount['Name'])
					if volu not in volumes:
						alert_message="Volume '"+volu+"' is not available."
						self.errors.append(alert_message)
						logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
					else:
						logging.info(bcolors.OKGREEN+"Volume '"+volu+"' is available"+bcolors.ENDC)
					resp['volume'].append(volu)
		resp['container_with_volume']=vol_container_count
		return resp


	def get_container_stats(self, _condata, temp):
		stat=(_condata.stats(decode=False, stream=False))
		sta = Stats(stat)

		cpu_total_usage=(sta.cpu_stats_total_usage())

		# Memory usage
		mem_u = sta.memory_stats_usage()
		# Memory limit
		mem_l = sta.memory_stats_limit()
		# Memory usage %
		# logging.info ("\n#Memory usage %")
		mem_u_p = int(mem_u)*100/int(mem_l) if mem_u else 0
		temp['mem_usage']=mem_u
		temp['mem_limit']=mem_l
		temp['mem_usage_per']=mem_u_p
		temp['cpu_total_usage']=cpu_total_usage

		inter=sta.interfaces()
		if inter:
			inter=ast.literal_eval(inter)
			temp['received_bytes']=sta.rx_bytes(inter[0])
			temp['transmitted_bytes']=sta.rx_bytes(inter[0])

	def parse_service_data(self, servdata, nids=[], volumes=[]):
		resp={}
		down_network={}
		up_network={}
		con_services=None
		resp['no_of_services']=len(servdata)
		logging.info(bcolors.CYAN+"-----Total Services : "+str(resp['no_of_services'])+"----------------------"+bcolors.ENDC)
		resp['services']=[]
		for k, d in enumerate(servdata):
			d=d.attrs
			temp={}
			temp['name']=d['Spec']['Name']
			temp['created_at']=d['CreatedAt']

			if 'Replicated' in d['Spec']['Mode']:
				temp['replicas']=d['Spec']['Mode']['Replicated']['Replicas']
			temp['id']=d['ID']
			if 'com.docker.stack.image' in d['Spec']['Labels']:
				temp['stack_image']=d['Spec']['Labels']['com.docker.stack.image']
			temp['image']=d['Spec']['TaskTemplate']['ContainerSpec']['Image']
			temp['network']=[]
			temp['volume']=[]

			if 'Networks' in d['Spec']['TaskTemplate']:
				for ne in d['Spec']['TaskTemplate']['Networks']:
					nid=str(ne['Target'])
					if nid not in nids:
						down_network[nid]=1
					else:
						up_network[nid]=1
					temp['network'].append(nid)
			resp['services'].append(temp)


			# logging.info(bcolors.CYAN+"-----Service "+str(k)+"------------------------------"+bcolors.ENDC)
			# logging.info("Name : "+str(temp['name']))
			# logging.info("Replicas : "+str(temp.get('replicas', None)))
			# logging.info("Image : "+str(temp['image']))
			# logging.info("Networks : "+str(temp['network']))
			# logging.info(bcolors.CYAN+"----------------------------------------------"+bcolors.ENDC)

			con_services = CONFIG['service']
			if temp['name'] in CONFIG['service']:
				currepl = temp.get('replicas', None)
				conrepl = CONFIG['service'][temp['name']]['replicas']
				if currepl and conrepl < currepl:
					alert_message=temp['name'] + " : extra "+ str(currepl - conrepl)+" more replicas running."
					self.errors.append(alert_message)
					logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
				elif currepl and conrepl > currepl:
					alert_message=temp['name'] + " : need "+ str(conrepl - currepl)+" more replicas."
					self.errors.append(alert_message)
					logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
				elif currepl and conrepl == currepl:
					logging.info(bcolors.OKGREEN+temp['name'] + " : Replicas mached!"+bcolors.ENDC)
				elif currepl:
					alert_message=temp['name'] + " : Replicas doesn't mached!"
					self.errors.append(alert_message)
					logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
				con_services.pop(temp['name'], None)

		for ms in con_services:
			alert_message=ms + " : Service down!"
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)

		# logging.info(json.dumps(resp))
		if len(down_network) > 0:
			alert_message=str(len(down_network))+": Networks is not available"
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
			alert_message=str(down_network)
			self.errors.append(alert_message)
			logging.error(bcolors.FAIL+alert_message+bcolors.ENDC)
		else:
			logging.info(bcolors.OKGREEN+str(len(up_network))+": All Networks are available"+bcolors.ENDC)
		return resp


	def get_all_network_ids(self, netdata):
		ids=[str(net.id) for net in netdata]
		return ids

	def get_all_volume_names(self, voldata):
		volnames=[str(vol.name) for vol in voldata]
		return volnames



m=Monitor()
m.scan_nodes()