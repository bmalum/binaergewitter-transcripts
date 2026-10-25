#!/bin/bash
# EC2 user data for a GPU instance (used: g6.12xlarge, 4x NVIDIA L4, Deep Learning Base OSS Nvidia Driver AMI,
# Ubuntu 22.04). Replace __BUCKET__ / __REGION__ before use. The instance needs an instance profile that can
# read/write the bucket, outbound internet (Hugging Face, download.binaergewitter.de) and no inbound access.
# Launch with --instance-initiated-shutdown-behavior terminate so the final shutdown terminates it.
shutdown -P +240   # hard safety net: power off (= terminate) after 4 h no matter what
exec > /var/log/bg-boot.log 2>&1
set -x
export HOME=/root DEBIAN_FRONTEND=noninteractive AWS_DEFAULT_REGION=__REGION__ BG_REGION=__REGION__ BG_BUCKET=__BUCKET__
mkdir -p /opt/bg && cd /opt/bg
apt-get update -q && apt-get install -yq ffmpeg libsndfile1
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
uv venv /opt/venv -p 3.11
uv pip install -p /opt/venv "nemo_toolkit[asr]==2.7.3" "speechbrain==1.1.2" "ruamel.yaml<0.18.15" "boto3"
PY=/opt/venv/bin/python
for f in worker.py supervise.sh; do
  $PY -c "import boto3,sys; boto3.client('s3').download_file('$BG_BUCKET', 'code/' + sys.argv[1], '/opt/bg/' + sys.argv[1])" $f
done
# warm the model caches once so the per-GPU workers don't race on the same downloads
$PY -c "
import nemo.collections.asr as a; a.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3')
from speechbrain.inference.speaker import EncoderClassifier as E; E.from_hparams('speechbrain/spkrec-ecapa-voxceleb', savedir='/opt/bg/ecapa-warm')
"
# one worker per GPU, restarted after CUDA errors; uploads logs and shuts down (= terminates) when the queue is empty
exec bash /opt/bg/supervise.sh
