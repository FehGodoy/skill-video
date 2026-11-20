"""Gera as imagens de um vídeo no Kaggle (GPU grátis) pela API, sem navegador.

Uso: python motor/imagens_kaggle.py videos/<slug>
Passos: cria o notebook -> `kaggle kernels push` -> espera terminar -> baixa imagens.zip
        -> extrai em videos/<slug>/imagens/<id>.png
Requer KAGGLE_API_TOKEN no .env (token de "API Tokens" do Kaggle).
"""
import json, os, pathlib, re, shutil, subprocess, sys, time, zipfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
for linha in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in linha and not linha.strip().startswith("#"):
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

CANAIS = json.loads((RAIZ / "canais.json").read_text(encoding="utf-8"))
USUARIO = CANAIS["kaggle_usuario"]
NEG = ("logo, emblem, badge, brand name, text, letters, words, watermark, signature, cartoon, illustration, "
       "3d render, cgi, deformed, disfigured, bad anatomy, extra fingers, mutated hands, blurry, low quality")


def kaggle(*args, check=True):
    r = subprocess.run([sys.executable, "-m", "kaggle", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"kaggle {' '.join(args)} falhou:\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def notebook(itens):
    def cel(src):
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": src}
    return {"cells": [
        cel("!pip install -q -U diffusers transformers accelerate safetensors"),
        cel("import os, shutil, time, torch\n"
            "from diffusers import StableDiffusionXLPipeline, AutoencoderKL, DPMSolverMultistepScheduler\n"
            "OUT = '/kaggle/working/imagens'\nos.makedirs(OUT, exist_ok=True)\n"
            "vae = AutoencoderKL.from_pretrained('madebyollin/sdxl-vae-fp16-fix', torch_dtype=torch.float16)\n"
            "pipe = StableDiffusionXLPipeline.from_pretrained('SG161222/RealVisXL_V4.0', vae=vae, torch_dtype=torch.float16)\n"
            "pipe.scheduler = DPMSolverMultistepScheduler.from_config(pipe.scheduler.config, algorithm_type='dpmsolver++', final_sigmas_type='sigma_min', use_karras_sigmas=True)\n"
            "pipe = pipe.to('cuda')\npipe.set_progress_bar_config(disable=True)   # sem barras: saída leve"),
        cel(f"ITENS = {json.dumps(itens, ensure_ascii=False)}\nNEG = {json.dumps(NEG)}\n"
            "t0 = time.time()\n"
            "for n, (iid, prompt) in enumerate(ITENS, 1):\n"
            "    g = torch.Generator('cuda').manual_seed(42)\n"
            "    img = pipe(prompt=prompt, negative_prompt=NEG, width=1024, height=576, num_inference_steps=25, guidance_scale=6, generator=g).images[0]\n"
            "    img.save(f'{OUT}/{iid}.png')\n"
            "    if n % 20 == 0: print(f'{n}/{len(ITENS)}  {time.time()-t0:.0f}s', flush=True)\n"
            "shutil.make_archive('/kaggle/working/imagens', 'zip', OUT)\n"
            "shutil.rmtree(OUT)   # deixa só o zip na saída\n"
            "print('PRONTO', len(ITENS), 'imagens')"),
    ], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                    "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def main():
    if not os.environ.get("KAGGLE_API_TOKEN"):
        raise SystemExit("Falta KAGGLE_API_TOKEN no .env (Kaggle > Settings > API Tokens > Generate New Token).")
    pasta = RAIZ / sys.argv[1]
    slug = re.sub(r"[^a-z0-9-]", "-", pasta.name.lower())
    rot = json.loads((pasta / "roteiro.json").read_text(encoding="utf-8"))
    itens = [[im["id"], f"{im['prompt']}, {rot['estilo_imagem']}"]
             for c in rot["cenas"] for f in c["falas"] for im in f.get("imagens", [])]
    kdir = pasta / "kaggle"; kdir.mkdir(exist_ok=True)
    (kdir / "imagens.ipynb").write_text(json.dumps(notebook(itens), ensure_ascii=False), encoding="utf-8")
    ref = f"{USUARIO}/skill-video-{slug}"
    (kdir / "kernel-metadata.json").write_text(json.dumps({
        "id": ref, "title": f"skill-video-{slug}", "code_file": "imagens.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_internet": True,
        "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
    }, indent=1), encoding="utf-8")

    print(f"enviando {len(itens)} prompts para {ref} ...")
    print(kaggle("kernels", "push", "-p", str(kdir)).strip())
    t0 = time.time()
    while True:
        time.sleep(60)
        st = kaggle("kernels", "status", ref, check=False).lower()
        mins = (time.time() - t0) / 60
        if "complete" in st:
            print(f"pronto em {mins:.0f} min"); break
        if "error" in st or "cancel" in st:
            raise SystemExit(f"o notebook falhou no Kaggle ({st.strip()}). Veja o log em https://www.kaggle.com/code/{ref}")
        print(f"  ... rodando ({mins:.0f} min)", flush=True)
        if mins > 180:
            raise SystemExit("passou de 3 h; verifique no Kaggle")

    baixa = kdir / "saida"; shutil.rmtree(baixa, ignore_errors=True); baixa.mkdir()
    kaggle("kernels", "output", ref, "-p", str(baixa))
    destino = pasta / "imagens"; destino.mkdir(exist_ok=True)
    with zipfile.ZipFile(baixa / "imagens.zip") as z:
        z.extractall(destino)
    shutil.rmtree(baixa)
    faltam = [i for i, _ in itens if not (destino / f"{i}.png").exists()]
    print(f"{len(itens) - len(faltam)} imagens em {destino}" + (f" | faltando: {faltam}" if faltam else ""))


if __name__ == "__main__":
    main()
