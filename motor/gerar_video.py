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

    if "--enviar" in sys.argv:
        cmd = ["youtube/upload.py", "upload", "--canal", rot["canal"], "--video", f"{rel}/video.mp4",
               "--titulo", rot["titulo"], "--descricao", rot["descricao"], "--tags", rot["tags"]]
        if (pasta / "thumb.png").exists():
            cmd += ["--thumb", f"{rel}/thumb.png"]
        etapa("envio ao YouTube (privado)", *cmd)
    print(f"\n==> pronto: {pasta / 'video.mp4'}")


if __name__ == "__main__":
    main()
