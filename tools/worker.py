"""One worker per GPU. Claims episodes from the shared S3 worklist (conditional put = lock),
transcribes with Parakeet TDT 0.6b v3 (20-min chunks cut at quiet points) and stores, per episode:
  out/<base>.asr.json  words, sentence segments, timings
  out/<base>.emb.npy   ECAPA embedding per sentence (float16, NaN rows for sentences < 0.8 s)
Speaker naming happens offline from the embeddings.
Usage: CUDA_VISIBLE_DEVICES=i worker.py <bucket> <worker-id> <main|retry>
  main : episodes without output, claimed under claims2/; a CUDA error exits with code 3 (supervisor restarts us,
         because a CUDA error poisons the whole process context)
  retry: episodes still without output after main, fp32 + 10-min chunks, claimed under retry/
"""
import io, json, os, subprocess, sys, time, traceback, urllib.request

import boto3
import numpy as np
import torch
from botocore.exceptions import ClientError

BUCKET, WID, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
CLAIM_PREFIX = "claims2" if MODE == "main" else "retry"
CHUNK_S = 1200 if MODE == "main" else 600
s3 = boto3.client("s3", region_name=os.environ.get("BG_REGION"))
TMP = f"/opt/bg/tmp/{WID}"
os.makedirs(TMP, exist_ok=True)
SR = 16000


def log(*a):
    print(time.strftime("%H:%M:%S"), WID, *a, flush=True)


def claim(base):
    try:
        s3.put_object(Bucket=BUCKET, Key=f"{CLAIM_PREFIX}/{base}", Body=WID.encode(), IfNoneMatch="*")
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("PreconditionFailed", "ConditionalRequestConflict"):
            return False
        raise


def quiet_cuts(audio, every_s=1200, search_s=20):
    cuts, t = [0], every_s
    while t < len(audio) / SR - 60:
        lo, hi = int((t - search_s) * SR), int((t + search_s) * SR)
        fr = audio[lo:hi][: (hi - lo) // 1600 * 1600].reshape(-1, 1600)
        cuts.append(lo + int(np.argmin((fr ** 2).mean(1))) * 1600 + 800)
        t += every_s
    cuts.append(len(audio))
    return cuts


import nemo.collections.asr as nemo_asr
from speechbrain.inference.speaker import EncoderClassifier

asr = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3").cuda().eval()
asr.change_attention_model("rel_pos_local_attn", [256, 256])
asr.change_subsampling_conv_chunking_factor(1)
# The CUDA-graph TDT greedy decoder hit CUDA_ERROR_ILLEGAL_ADDRESS on some episodes; use the plain loop.
from omegaconf import open_dict
dc = asr.cfg.decoding
with open_dict(dc):
    dc.greedy.use_cuda_graph_decoder = False
asr.change_decoding_strategy(dc, verbose=False)
ecapa = EncoderClassifier.from_hparams("speechbrain/spkrec-ecapa-voxceleb", savedir=f"/opt/bg/ecapa-{WID}",
                                       run_opts={"device": "cuda"})
work = json.loads(s3.get_object(Bucket=BUCKET, Key="worklist.json")["Body"].read())
if os.environ.get("BG_ONLY"):  # test hook: process exactly one episode, claim under test/
    work, CLAIM_PREFIX = [{"base": os.environ["BG_ONLY"]}], "test"


def done_set():
    keys, tok = set(), None
    while True:
        kw = {"Bucket": BUCKET, "Prefix": "out/"}
        if tok:
            kw["ContinuationToken"] = tok
        r = s3.list_objects_v2(**kw)
        keys |= {o["Key"][4:-9] for o in r.get("Contents", []) if o["Key"].endswith(".asr.json")}
        if not r.get("IsTruncated"):
            return keys
        tok = r["NextContinuationToken"]


log("ready", MODE, len(work), "items")


@torch.no_grad()
def embed(audio, segs, min_len=0.8, max_len=15.0):
    out = np.full((len(segs), 192), np.nan, dtype=np.float16)
    for i, (s, e, _) in enumerate(segs):
        if e - s < min_len:
            continue
        e = min(e, s + max_len)
        x = torch.from_numpy(audio[int(s * SR):int(e * SR)]).cuda()[None]
        v = ecapa.encode_batch(x).squeeze().float().cpu().numpy()
        out[i] = v / np.linalg.norm(v)
    return out


def process(base):
    t0 = time.time()
    mp3 = f"{TMP}/a.mp3"
    urllib.request.urlretrieve(f"https://download.binaergewitter.de/{base}.mp3", mp3)
    raw = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], check=True, capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32).copy()
    t_dl = time.time() - t0
    t1 = time.time()
    cuts = quiet_cuts(audio, every_s=CHUNK_S)
    words, segs = [], []
    for a, b in zip(cuts, cuts[1:]):
        off = a / SR
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=MODE == "main"):
            hyp = asr.transcribe([audio[a:b]], timestamps=True, batch_size=1, verbose=False)[0]
        words += [(w["word"], round(w["start"] + off, 2), round(w["end"] + off, 2)) for w in hyp.timestamp["word"]]
        segs += [(round(s["start"] + off, 2), round(s["end"] + off, 2), s["segment"]) for s in hyp.timestamp["segment"]]
    torch.cuda.empty_cache()
    t_asr = time.time() - t1
    t2 = time.time()
    emb = embed(audio, segs)
    t_emb = time.time() - t2
    dur = len(audio) / SR
    meta = {"base": base, "duration_s": round(dur, 1), "chunks": len(cuts) - 1, "worker": WID, "mode": MODE,
            "t_download_decode": round(t_dl, 1), "t_asr": round(t_asr, 1), "t_embed": round(t_emb, 1),
            "words": words, "segments": segs, "model": "nvidia/parakeet-tdt-0.6b-v3",
            "embedder": "speechbrain/spkrec-ecapa-voxceleb"}
    buf = io.BytesIO(); np.save(buf, emb)
    s3.put_object(Bucket=BUCKET, Key=f"out/{base}.emb.npy", Body=buf.getvalue())
    s3.put_object(Bucket=BUCKET, Key=f"out/{base}.asr.json", Body=json.dumps(meta, ensure_ascii=False).encode())
    log("done", base, f"{dur/60:.0f} min", f"dl {t_dl:.0f}s asr {t_asr:.0f}s emb {t_emb:.0f}s")


done = done_set()
for item in work:
    base = item["base"]
    if base in done or not claim(base):
        continue
    try:
        process(base)
    except Exception:
        tb = traceback.format_exc()
        log("FAILED", base, tb[-300:])
        s3.put_object(Bucket=BUCKET, Key=f"errors-{MODE}/{base}.txt", Body=tb.encode())
        if "CUDA" in tb or "cuda" in tb:
            log("CUDA error -> exiting so the supervisor restarts with a fresh context")
            os._exit(3)
log("queue empty", MODE)
