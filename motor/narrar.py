"""Narração por cena com a Cartesia (WebSocket) + tempo de cada palavra.

Uso: python motor/narrar.py videos/<slug>
Gera  videos/<slug>/audio/cena_XX.wav  e  videos/<slug>/narracao.json
"""
import base64, json, os, pathlib, re, sys, uuid, wave

import websocket

RAIZ = pathlib.Path(__file__).resolve().parent.parent
for linha in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linha and not linha.strip().startswith("#"):
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

SR = 44100
URL = "wss://api.cartesia.ai/tts/websocket?cartesia_version=2026-03-01"


def limpar(texto):
    return texto.replace("*", "")


def sintetizar(texto, voz, idioma):
    ws = websocket.create_connection(URL, header=[f"X-API-Key: {os.environ['CARTESIA_API_KEY']}"])
    try:
        ws.send(json.dumps({
            "model_id": "sonic-3", "transcript": texto,
            "voice": {"mode": "id", "id": voz}, "language": idioma,
            "context_id": str(uuid.uuid4()),
            "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": SR},
            "add_timestamps": True, "continue": False,
            "generation_config": {"speed": VELOCIDADE},
        }))
        audio, palavras, ini, fim = [], [], [], []
        while True:
            m = json.loads(ws.recv())
            if m.get("type") == "error":
                raise SystemExit(f"Cartesia: {m}")
            if m.get("type") == "chunk":
                audio.append(base64.b64decode(m["data"]))
            elif m.get("type") == "timestamps":
                wt = m.get("word_timestamps", {})
                palavras += wt.get("words", []); ini += wt.get("start", []); fim += wt.get("end", [])
            elif m.get("type") == "done":
                break
    finally:
        ws.close()
    return b"".join(audio), palavras, ini, fim


def main():
    pasta = RAIZ / sys.argv[1]
    rot = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    global VELOCIDADE
    VELOCIDADE = rot.get("velocidade", 1.0)
    (pasta / "audio").mkdir(exist_ok=True)
    saida = []
    for ci, cena in enumerate(rot["cenas"], 1):
        texto = " ".join(limpar(f["texto"]) for f in cena["falas"])
        pcm, pal, ini, fim = sintetizar(texto, rot["voice_id"], rot["language"])
        arq = pasta / "audio" / f"cena_{ci:02d}.wav"
        with wave.open(str(arq), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
        dur = len(pcm) / (SR * 2)
        # início de cada fala = início da sua primeira palavra (contando palavras do texto)
        inicios, k = [], 0
        for f in cena["falas"]:
            inicios.append(ini[k] if k < len(ini) else (ini[-1] if ini else 0.0))
            k += len(limpar(f["texto"]).split())
        saida.append({"duracao": round(dur, 3), "falas_inicio": inicios,
                      "palavras": pal, "inicio": ini, "fim": fim})
        print(f"cena {ci:02d}: {dur:5.1f}s  ({len(pal)} palavras)")
    (pasta / "narracao.json").write_text(json.dumps(saida, ensure_ascii=False), encoding="utf-8")
    print(f"total: {sum(s['duracao'] for s in saida) / 60:.1f} min")


if __name__ == "__main__":
    main()
