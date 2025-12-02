import boto3
import requests
import time

# -----------------------------
# 參數設定
# -----------------------------
REGION = "us-east-1"
TEMPLATE_NAME = "tooplate-template"  # Tooplate 模板名稱

# 自動抓公開 IP
MY_IP = requests.get("https://api.ipify.org").text + "/32"
print(f"Detected public IP: {MY_IP}")

# -----------------------------
# 建立 Boto3 客戶端
# -----------------------------
ec2_client = boto3.client("ec2", region_name=REGION)
elb_client = boto3.client("elbv2", region_name=REGION)

# -----------------------------
# 1. 建立 Key Pair (檢查是否存在)
# -----------------------------
key_pair_name = f"{TEMPLATE_NAME}-key"
existing_keys = ec2_client.describe_key_pairs()['KeyPairs']
if any(k['KeyName'] == key_pair_name for k in existing_keys):
    print(f"Key Pair {key_pair_name} already exists, skipping creation.")
else:
    key_pair = ec2_client.create_key_pair(KeyName=key_pair_name)
    with open(f"{key_pair_name}.pem", "w") as f:
        f.write(key_pair['KeyMaterial'])
    print(f"Created Key Pair: {key_pair_name}")

# -----------------------------
# 2. 建立 Security Group
# -----------------------------
sg_name = f"{TEMPLATE_NAME}-sg"
vpc_id = ec2_client.describe_vpcs()['Vpcs'][0]['VpcId']

sg = ec2_client.create_security_group(
    GroupName=sg_name,
    Description="Allow SSH from my IP and HTTP from anywhere",
    VpcId=vpc_id
)
sg_id = sg['GroupId']

# 設定 ingress 規則
ec2_client.authorize_security_group_ingress(
    GroupId=sg_id,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 22,
            'ToPort': 22,
            'IpRanges': [{'CidrIp': MY_IP}]
        },
        {
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
    ]
)
print(f"Created Security Group: {sg_name} ({sg_id})")

# -----------------------------
# 3. 建立 EC2 Instance
# -----------------------------
user_data_script = f"""#!/bin/bash
yum update -y
yum install -y httpd unzip wget
systemctl enable httpd
systemctl start httpd
cd /var/www/html
wget https://www.tooplate.com/zip-templates/{TEMPLATE_NAME}.zip
unzip {TEMPLATE_NAME}.zip
"""

instance = ec2_client.run_instances(
    ImageId="ami-0a887e401f7654935",  # Amazon Linux 2023
    InstanceType="t3.micro",
    KeyName=key_pair_name,
    SecurityGroupIds=[sg_id],
    UserData=user_data_script,
    MinCount=1,
    MaxCount=1
)
instance_id = instance['Instances'][0]['InstanceId']
print(f"EC2 Instance {instance_id} launching...")

# 等待 EC2 啟動
ec2_client.get_waiter('instance_running').wait(InstanceIds=[instance_id])
instance_desc = ec2_client.describe_instances(InstanceIds=[instance_id])
subnet_id = instance_desc['Reservations'][0]['Instances'][0]['SubnetId']
print(f"EC2 Instance {instance_id} is running in subnet {subnet_id}")

# -----------------------------
# 4. 建立 ALB Security Group
# -----------------------------
alb_sg_name = f"{TEMPLATE_NAME}-alb-sg"
alb_sg = ec2_client.create_security_group(
    GroupName=alb_sg_name,
    Description="ALB allow HTTP",
    VpcId=vpc_id
)
alb_sg_id = alb_sg['GroupId']

# Allow HTTP
ec2_client.authorize_security_group_ingress(
    GroupId=alb_sg_id,
    IpPermissions=[{
        'IpProtocol': 'tcp',
        'FromPort': 80,
        'ToPort': 80,
        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
    }]
)

# 取得可用子網路
subnets = [s['SubnetId'] for s in ec2_client.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc_id]}])['Subnets']]

# -----------------------------
# 5. 建立 ALB
# -----------------------------
alb_name = f"{TEMPLATE_NAME}-alb"
alb = elb_client.create_load_balancer(
    Name=alb_name,
    Subnets=subnets,
    SecurityGroups=[alb_sg_id],
    Scheme='internet-facing',
    Type='application',
    IpAddressType='ipv4'
)
alb_arn = alb['LoadBalancers'][0]['LoadBalancerArn']
alb_dns = alb['LoadBalancers'][0]['DNSName']
print(f"Created ALB: {alb_name} ({alb_dns})")

# -----------------------------
# 6. 建立 Target Group
# -----------------------------
tg_name = f"{TEMPLATE_NAME}-tg"
tg = elb_client.create_target_group(
    Name=tg_name,
    Protocol='HTTP',
    Port=80,
    VpcId=vpc_id,
    TargetType='instance',
    HealthCheckProtocol='HTTP',
    HealthCheckPath='/',
)
tg_arn = tg['TargetGroups'][0]['TargetGroupArn']

# -----------------------------
# 7. 建立 Listener
# -----------------------------
elb_client.create_listener(
    LoadBalancerArn=alb_arn,
    Protocol='HTTP',
    Port=80,
    DefaultActions=[{
        'Type': 'forward',
        'TargetGroupArn': tg_arn
    }]
)

# -----------------------------
# 8. 註冊 EC2 到 Target Group
# -----------------------------
elb_client.register_targets(
    TargetGroupArn=tg_arn,
    Targets=[{'Id': instance_id, 'Port': 80}]
)

print(f"EC2 {instance_id} registered to Target Group {tg_name}")
print(f"ALB Endpoint: http://{alb_dns}")
