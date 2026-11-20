"""Gera a narração de cada cena com a Cartesia (bytes API, WAV) e salva a duração."""
import json, os, wave, pathlib, requests

BASE = pathlib.Path(__file__).parent
for line in (BASE.parent / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

key = os.environ["CARTESIA_API_KEY"]
rot = json.loads((BASE / "roteiro.json").read_text(encoding="utf-8"))
out = BASE / "audio"; out.mkdir(exist_ok=True)

for i, c in enumerate(rot["cenas"], 1):
    r = requests.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={"X-API-Key": key, "Cartesia-Version": "2026-03-01", "Content-Type": "application/json"},
        json={
            "model_id": "sonic-3",
            "transcript": c["texto"],
            "voice": {"mode": "id", "id": rot["voice_id"]},
            "language": rot["language"],
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": 44100},
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise SystemExit(f"cena {i}: erro {r.status_code} {r.text[:300]}")
    p = out / f"{i:03d}.wav"
    p.write_bytes(r.content)
    with wave.open(str(p)) as w:
        c["duracao"] = round(w.getnframes() / w.getframerate(), 2)
    print(f"cena {i}: {c['duracao']}s")

(BASE / "roteiro.json").write_text(json.dumps(rot, ensure_ascii=False, indent=2), encoding="utf-8")
