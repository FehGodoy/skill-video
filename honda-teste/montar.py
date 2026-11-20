"""Monta o vídeo de teste: imagem com zoom lento + narração + legendas queimadas."""
import json, pathlib, subprocess, re

BASE = pathlib.Path(__file__).parent
rot = json.loads((BASE / "roteiro.json").read_text(encoding="utf-8"))
ESCOLHA = {"001": "a", "002": "b", "003": "b", "004": "a", "005": "a"}  # melhor variação de cada cena
FPS, PAUSA = 30, 0.35
tmp = BASE / "tmp"; tmp.mkdir(exist_ok=True)


def ts(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def chunks(texto, n=6):
    w = texto.split()
    return [" ".join(w[i:i + n]) for i in range(0, len(w), n)]


ass = ["[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginV",
       "Style: Leg,Arial,68,&H00FFFFFF,&H00000000,&H80000000,-1,1,5,2,2,90", "",
       "[Events]", "Format: Layer, Start, End, Style, Text"]

clips, t0 = [], 0.0
for i, c in enumerate(rot["cenas"], 1):
    dur = c["duracao"] + PAUSA
    frames = int(dur * FPS)
    img = BASE / "imagens" / f"{c['imagem']}_{ESCOLHA[c['imagem']]}.png"
    aud = BASE / "audio" / f"{i:03d}.wav"
    # zoom-in nas cenas ímpares, zoom-out nas pares
    z = "min(1+0.10*on/{f},1.10)".format(f=frames) if i % 2 else "max(1.10-0.10*on/{f},1.0)".format(f=frames)
    vf = (f"scale=3840:2160,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1920x1080:fps={FPS},"
          f"fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.2f}:d=0.25,format=yuv420p")
    out = tmp / f"cena{i:03d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(img), "-i", str(aud),
                    "-vf", vf, "-af", f"apad=pad_dur={PAUSA}", "-t", f"{dur:.2f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k",
                    "-ar", "44100", str(out)], check=True)
    clips.append(out)
    # legendas: blocos de ~6 palavras, tempo proporcional ao número de letras
    partes = chunks(c["texto"])
    total = sum(len(p) for p in partes)
    t = t0
    for p in partes:
        d = c["duracao"] * len(p) / total
        ass.append(f"Dialogue: 0,{ts(t)},{ts(t + d)},Leg,{p}")
        t += d
    t0 += dur
    print(f"cena {i} ok ({dur:.1f}s)")

(tmp / "lista.txt").write_text("".join(f"file '{p.name}'\n" for p in clips), encoding="utf-8")
(tmp / "legendas.ass").write_text("\n".join(ass), encoding="utf-8")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "lista.txt",
                "-vf", "subtitles=legendas.ass", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                "-c:a", "copy", "../honda_teste.mp4"], cwd=tmp, check=True)
print(f"pronto: honda_teste.mp4 ({t0:.1f}s)")
