import runpod
import requests
import time
import json
import base64
import os
import subprocess

print("=" * 50)
print("🚀 HANDLER ЗАПУЩЕН")
print("=" * 50)

# ============================================
# ЗАПУСК COMFYUI (ОДИН РАЗ ПРИ СТАРТЕ)
# ============================================

comfy_process = None

def start_comfy():
    global comfy_process
    if comfy_process is None:
        print("🚀 Starting ComfyUI in background...")
        comfy_process = subprocess.Popen(
            ["python", "/comfyui/main.py", "--listen", "0.0.0.0", "--port", "8188"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        for i in range(30):
            try:
                requests.get("http://localhost:8188", timeout=2)
                print("✅ ComfyUI is ready!")
                return True
            except:
                print(f"⏳ Waiting for ComfyUI... ({i+1}/30)")
                time.sleep(2)
        print("❌ ComfyUI failed to start")
        return False
    return True

# ============================================
# ЗАГРУЗКА WORKFLOW
# ============================================

def load_workflow():
    workflow_path = "/comfyui/workflow.json"
    try:
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
            print(f"✅ Workflow loaded from {workflow_path}")
            return workflow
    except FileNotFoundError:
        print(f"❌ Workflow file not found at {workflow_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        raise

def update_prompt(workflow, text):
    """Обновляет промпт в ноде 134 (UI-формат)"""
    for node in workflow.get('nodes', []):
        if node.get('id') == 134 and node.get('type') == 'CLIPTextEncode':
            node['widgets_values'] = [text]
            print(f"✅ Prompt updated in node 134: {text[:50]}...")
            return workflow
    raise Exception("CLIPTextEncode node 134 not found")

def update_image(workflow, filename):
    """Обновляет имя файла в ноде 148 (UI-формат)"""
    for node in workflow.get('nodes', []):
        if node.get('id') == 148 and node.get('type') == 'LoadImage':
            node['widgets_values'] = [filename, "image"]
            print(f"✅ Image updated in node 148: {filename}")
            return workflow
    raise Exception("LoadImage node 148 not found")

# ============================================
# ОСНОВНОЙ ХЕНДЛЕР
# ============================================

def handler(job):
    print(f"📥 Received job: {job.get('id')}")
    
    job_input = job.get("input", {})
    prompt = job_input.get("prompt")
    image_base64 = job_input.get("image")
    
    print(f"📝 Prompt: {prompt[:50] if prompt else 'None'}...")
    print(f"🖼️ Image size: {len(image_base64) if image_base64 else 0} chars")
    
    if not prompt:
        return {"error": "Missing 'prompt' in input"}
    if not image_base64:
        return {"error": "Missing 'image' in input"}
    
    # 1. Запускаем ComfyUI
    if not start_comfy():
        return {"error": "ComfyUI failed to start"}
    
    # 2. Сохраняем изображение
    os.makedirs("/comfyui/input", exist_ok=True)
    image_filename = "input.jpg"
    try:
        img_data = base64.b64decode(image_base64)
        with open(f"/comfyui/input/{image_filename}", "wb") as f:
            f.write(img_data)
        print(f"✅ Image saved: {image_filename}")
    except Exception as e:
        return {"error": f"Failed to save image: {str(e)}"}
    
    # 3. Загружаем и модифицируем workflow
    try:
        workflow = load_workflow()
        workflow = update_prompt(workflow, prompt)
        workflow = update_image(workflow, image_filename)
    except Exception as e:
        return {"error": f"Workflow error: {str(e)}"}
    
    # 4. Отправляем workflow в ComfyUI
    print("📤 Sending workflow to ComfyUI...")
    try:
        response = requests.post("http://localhost:8188/prompt", json={"prompt": workflow}, timeout=30)
        if response.status_code != 200:
            return {"error": f"ComfyUI error: {response.text}"}
        
        result = response.json()
        prompt_id = result.get('prompt_id')
        if not prompt_id:
            return {"error": f"No prompt_id: {result}"}
        
        print(f"🆔 ComfyUI Prompt ID: {prompt_id}")
    except Exception as e:
        return {"error": f"Failed to send workflow: {str(e)}"}
    
    # 5. Ждём результат
    print("🎬 Waiting for video generation...")
    for _ in range(120):
        time.sleep(5)
        try:
            history_resp = requests.get(f"http://localhost:8188/history/{prompt_id}", timeout=10)
            if history_resp.status_code == 200:
                history = history_resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get('outputs', {})
                    
                    for node_id, node_output in outputs.items():
                        if 'videos' in node_output and node_output['videos']:
                            video = node_output['videos'][0]
                            video_url = f"http://localhost:8188/view?filename={video['filename']}&type=output"
                            print(f"🎉 Video generated! URL: {video_url}")
                            return {"status": "completed", "video_url": video_url}
                        
                        if 'images' in node_output and node_output['images']:
                            img = node_output['images'][0]
                            img_url = f"http://localhost:8188/view?filename={img['filename']}&type=output"
                            print(f"🎉 Image generated! URL: {img_url}")
                            return {"status": "completed", "image_url": img_url}
        except Exception as e:
            print(f"⚠️ Error checking status: {e}")
    
    return {"error": "Generation timeout (10 minutes)"}

# ============================================
# ЗАПУСК СЕРВЕРЛЕС ВОРКЕРА
# ============================================

if __name__ == "__main__":
    print("🚀 Starting RunPod Serverless Worker...")
    runpod.serverless.start({"handler": handler})
