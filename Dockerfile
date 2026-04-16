FROM runpod/worker-comfyui:5.5.1-base

# Установка кастомных нод
RUN comfy node install --exit-on-fail ComfyUI-WanVideoWrapper@1.4.7 --mode remote
RUN comfy node install --exit-on-fail comfyui-wanvideowrapper@1.4.7
RUN comfy node install --exit-on-fail comfyui-kjnodes@1.3.6
RUN comfy node install --exit-on-fail comfyui-frame-interpolation@1.0.7
RUN comfy node install --exit-on-fail comfyui-custom-scripts@1.2.5
RUN comfy node install --exit-on-fail comfyui-easy-use@1.3.6

# Модели НЕ скачиваем — они на Volume
# Только копируем handler и workflow
COPY handler.py /handler.py
COPY Wan22.json /comfyui/workflow.json

CMD ["python", "-u", "/handler.py"]