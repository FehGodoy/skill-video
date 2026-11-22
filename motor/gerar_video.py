"""Roda o pipeline inteiro de um vídeo a partir do roteiro pronto.

Uso:
  python motor/gerar_video.py videos/<slug>            # narração + imagens + montagem
  python motor/gerar_video.py videos/<slug> --enviar   # ... e envia como PRIVADO no canal
Etapas já feitas são puladas (apague o arquivo para refazer):
  narracao.json -> imagens/ completas -> video.mp4
"""
import json, pathlib, subprocess, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable


def etapa(nome, *cmd):
    print(f"\n==> {nome}", flush=True)
    subprocess.run([PY, "-u", *cmd], cwd=RAIZ, check=True)


def capitulos(pasta, rot):
    """'0:00 Título' por cena, com os tempos reais da narração (mesma pausa do montador)."""
    sys.path.insert(0, str(RAIZ / "motor"))
    from montar import PAUSA
    narr = json.loads((pasta / "narracao.json").read_text(encoding="utf-8"))
    t, linhas = 0.0, []
    for cena, info in zip(rot["cenas"], narr):
        linhas.append(f"{int(t // 60)}:{int(t % 60):02d} {cena['titulo']}")
        t += info["duracao"] + PAUSA
    return "\n".join(linhas)


def descricao_final(pasta, rot):
    d = rot["descricao"]
    return d.replace("{capitulos}", capitulos(pasta, rot)) if "{capitulos}" in d else d


def main():
    rel = sys.argv[1]
    pasta = RAIZ / rel
    rot = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    ids = [im["id"] for c in rot["cenas"] for f in c["falas"] for im in f.get("imagens", [])]

    if not (pasta / "narracao.json").exists():
        etapa("narração (Cartesia)", "motor/narrar.py", rel)
    if not all((pasta / "imagens" / f"{i}.png").exists() for i in ids):
        etapa(f"imagens no Kaggle ({len(ids)})", "motor/imagens_kaggle.py", rel)
    if not (pasta / "video.mp4").exists():
        etapa("montagem", "motor/montar.py", rel)
    if not (pasta / "thumb.png").exists() and rot.get("thumb_prompt"):
        etapa("thumbnail (OpenAI)", "motor/thumb_ia.py", rel)

    if "--enviar" in sys.argv:
        cmd = ["youtube/upload.py", "upload", "--canal", rot["canal"], "--video", f"{rel}/video.mp4",
               "--titulo", rot["titulo"], "--descricao", descricao_final(pasta, rot), "--tags", rot["tags"]]
        if (pasta / "thumb.png").exists():
            cmd += ["--thumb", f"{rel}/thumb.png"]
        etapa("envio ao YouTube (privado)", *cmd)
    print(f"\n==> pronto: {pasta / 'video.mp4'}")


if __name__ == "__main__":
    main()
