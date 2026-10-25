#!/bin/bash
# Per GPU: run worker in main mode, restarting after CUDA crashes (max 25), then one retry pass.
# When all GPUs are finished: upload logs and terminate the instance.
export HOME=/root AWS_DEFAULT_REGION=${BG_REGION:?set BG_REGION (region of the bucket)}
B=${BG_BUCKET:?set BG_BUCKET (S3 bucket with code/, worklist.json; results go to out/)}
PY=/opt/venv/bin/python
TOKEN=$(curl -s -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 600")
IID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
NG=$(nvidia-smi -L | wc -l)
gpu_loop() {
  local i=$1 n=0
  for mode in main retry; do
    n=0
    while [ $n -lt 25 ]; do
      CUDA_VISIBLE_DEVICES=$i $PY /opt/bg/worker.py $B $IID-g$i $mode && break
      n=$((n + 1)); echo "restart $mode #$n"; sleep 3
    done
  done
}
for i in $(seq 0 $((NG - 1))); do
  gpu_loop $i > /opt/bg/s$i.log 2>&1 &
done
wait
for f in /var/log/bg-boot.log /opt/bg/w*.log /opt/bg/s*.log; do
  $PY -c "import boto3,sys; boto3.client('s3').upload_file(sys.argv[1], '$B', 'logs/$IID/' + sys.argv[1].split('/')[-1])" $f
done
shutdown -h now
