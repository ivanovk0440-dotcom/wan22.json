import runpod
import requests
import time
import json
import base64
import os

# --- Эта часть запускает ComfyUI один раз при старте воркера ---
comfy_process = None

def start_comfy():
    import subprocess
    global comfy_process
    if comfy_process is None:
        print("🚀 Starting ComfyUI in the background...")
        # Эта команда запускает ComfyUI и перенаправляет его вывод в "никуда", чтобы он не засорял логи.
        comfy_process = subprocess.Popen(
            ["python", "/comfyui/main.py", "--listen", "0.0.0.0", "--port", "8188"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Ждем, пока ComfyUI реально запустится и начнет слушать порт 8188.
        for i in range(30):
            try:
                requests.get("http://localhost:8188", timeout=2)
                print("✅ ComfyUI is ready!")
                return True
            except requests.exceptions.ConnectionError:
                print(f"⏳ Waiting for ComfyUI... ({i+1}/30)")
                time.sleep(2)
        print("❌ Error: ComfyUI failed to start")
        return False
    return True
# -------------------------------------------------------------

def handler(job):
    """
    Эта функция вызывается для каждого нового запроса к твоему эндпоинту.
    """
    print(f"📥 Received job: {job['id']}")

    # 1. Убеждаемся, что ComfyUI работает.
    if not start_comfy():
        return {"error": "ComfyUI failed to start"}

    # 2. Забираем входные данные от бота.
    job_input = job.get("input", {})
    workflow = job_input.get("workflow")
    images = job_input.get("images", [])

    if not workflow:
        return {"error": "Workflow is required in the input"}

    # 3. Сохраняем присланные пользователем изображения.
    for img in images:
        img_name = img.get('name', 'image.jpg')
        img_data = base64.b64decode(img.get('image'))
        # Убедимся, что папка для входящих файлов существует.
        os.makedirs("/comfyui/input", exist_ok=True)
        with open(f"/comfyui/input/{img_name}", "wb") as f:
            f.write(img_data)
        print(f"🖼️ Saved image: {img_name}")

    # 4. Отправляем workflow в ComfyUI.
    print("📤 Sending workflow to ComfyUI...")
    response = requests.post("http://localhost:8188/prompt", json={"prompt": workflow})

    if response.status_code != 200:
        return {"error": f"ComfyUI error: {response.text}"}

    # 5. Получаем ID задания от ComfyUI.
    prompt_id = response.json()['prompt_id']
    print(f"🆔 ComfyUI Prompt ID: {prompt_id}")

    # 6. Ждем окончания генерации, проверяя статус каждые 2 секунды.
    print("🎬 Waiting for video generation... (this can take a while)")
    for _ in range(600):  # Проверяем до 600 раз (600 * 2 сек = 20 минут)
        time.sleep(2)
        history_response = requests.get(f"http://localhost:8188/history/{prompt_id}")
        if history_response.status_code == 200:
            history = history_response.json()
            if prompt_id in history:
                outputs = history[prompt_id]['outputs']
                print(f"🔍 Outputs found: {list(outputs.keys())}")

                # Ищем результат в нодах, которые сохраняют видео или картинку.
                for node_id, node_output in outputs.items():
                    # Проверяем для ноды SaveVideo
                    if 'videos' in node_output and node_output['videos']:
                        video = node_output['videos'][0]
                        video_url = f"http://localhost:8188/view?filename={video['filename']}&type=output"
                        print(f"🎉 Video generated successfully!")
                        return {"status": "completed", "video_url": video_url}
                    # Проверяем для ноды SaveImage
                    if 'images' in node_output and node_output['images']:
                        image = node_output['images'][0]
                        image_url = f"http://localhost:8188/view?filename={image['filename']}&type=output"
                        print(f"🎉 Image generated successfully!")
                        return {"status": "completed", "image_url": image_url}

    # 7. Если цикл закончился, а результат не получен.
    return {"error": "Generation timeout (20 minutes)"}

# --- Эта часть запускает сам серверлес-воркер ---
if __name__ == "__main__":
    print("🚀 Starting RunPod Serverless Worker...")
    runpod.serverless.start({"handler": handler})
