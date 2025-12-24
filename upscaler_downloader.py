import os
import requests
import folder_paths
from server import PromptServer
from aiohttp import web
import urllib.parse

# ---------------------------------------
# Secure path join helper
# ---------------------------------------
def safe_join(base_dir, user_path):
    base = os.path.abspath(base_dir)
    final_path = os.path.abspath(os.path.join(base, user_path))

    # Ensure path is strictly inside base directory
    if os.path.commonpath([base, final_path]) != base:
        raise ValueError("Illegal path")

    return final_path


class UpscalerDownloader:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "upscaler_name": ("STRING", {"default": "example.pth"}),
                "download_url": ("STRING", {"default": "https://example.com/upscaler.pth"}),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "download_upscaler"
    OUTPUT_NODE = True
    CATEGORY = "utils"

    def download_upscaler(self, upscaler_name, download_url):
        # Real download handled via HTTP endpoint
        return ()


# ---------------------------------------
# Download Upscaler from URL -> save to server
# ---------------------------------------
@PromptServer.instance.routes.post("/upscaler_downloader/download")
async def download_upscaler_endpoint(request):
    try:
        data = await request.json()

        upscaler_name = data.get("upscaler_name", "").strip()
        download_url = data.get("download_url", "").strip()

        if not upscaler_name or not download_url:
            return web.json_response(
                {"error": "Missing upscaler_name or download_url"}, status=400
            )

        upscaler_directory = folder_paths.get_folder_paths("upscale_models")[0]

        try:
            file_path = safe_join(upscaler_directory, upscaler_name)
        except ValueError:
            return web.json_response({"error": "Illegal file path"}, status=403)

        # Create subfolders if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if os.path.exists(file_path):
            return web.json_response(
                {"message": f"File {upscaler_name} already exists"}, status=200
            )

        # Download file
        response = requests.get(download_url, stream=True, timeout=30)
        response.raise_for_status()

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return web.json_response(
            {"message": f"Successfully downloaded {upscaler_name}"}, status=200
        )

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------
# List all existing Upscaler files
# ---------------------------------------
@PromptServer.instance.routes.get("/upscaler_downloader/list")
async def list_upscalers_endpoint(request):
    try:
        upscaler_directory = folder_paths.get_folder_paths("upscale_models")[0]
        upscaler_files = []

        if os.path.exists(upscaler_directory):
            for root, dirs, files in os.walk(upscaler_directory):
                for file in files:
                    if file.endswith((".safetensors", ".ckpt", ".pt", ".pth")):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, upscaler_directory)
                        upscaler_files.append(
                            {
                                "name": relative_path,
                                "size": os.path.getsize(file_path),
                            }
                        )

        return web.json_response({"upscalers": upscaler_files}, status=200)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------
# Web UI (HTML embedded)
# ---------------------------------------
@PromptServer.instance.routes.get("/upscaler_downloader")
async def serve_upscaler_downloader_page(request):
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>ComfyUI 放大模型下载器</title>
<style>
body{font-family:Arial, sans-serif;max-width:1000px;margin:0 auto;background:#f5f5f5;padding:20px;}
.container{background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,.1);}
h1{text-align:center;color:#333;}
input,button{padding:10px;margin-top:5px;width:100%;}
button{cursor:pointer;}
.model-item{border-bottom:1px solid #eee;padding:6px 0;display:flex;justify-content:space-between;align-items:center;}
.download-btn{margin-left:10px;width:auto;background-color:#0275d8;color:white;border:none;border-radius:4px;padding:8px 12px;}
.download-btn:hover{background-color:#0260d0;}
.button-group{margin-bottom:15px;}
.button-group button{width:auto;display:inline-block;margin-right:10px;}
.refresh-btn{background-color:#5bc0de;color:white;border:none;border-radius:4px;}
.refresh-btn:hover{background-color:#31b0d5;}
.download-all-btn{background-color:#f0ad4e;color:white;border:none;border-radius:4px;}
.download-all-btn:hover{background-color:#ec971f;}
.submit-btn{background-color:#4CAF50;color:white;border:none;border-radius:4px;}
.submit-btn:hover{background-color:#45a049;}
.result{margin-top:20px;padding:15px;border-radius:4px;display:none;}
.success{background-color:#dff0d8;color:#3c763d;border:1px solid #d6e9c6;}
.error{background-color:#f2dede;color:#a94442;border:1px solid #ebccd1;}
.progress{margin-top:10px;font-size:14px;color:#666;}
</style>
</head>
<body>
<div class="container">
<h1>ComfyUI 放大模型下载器</h1>

<form id="downloadForm">
<input id="upscalerName" placeholder="例如: RealESRGAN_x4.pth" required>
<input id="downloadUrl" type="url" placeholder="https://example.com/model.pth" required>
<button type="submit" class="submit-btn">下载放大模型</button>
</form>

<div id="result" class="result"></div>

<h3>已有放大模型</h3>
<div class="button-group">
<button id="refreshBtn" class="refresh-btn">刷新列表</button>
<button id="downloadAllBtn" class="download-all-btn">全部下载到本地</button>
</div>
<div id="modelList"></div>
<div id="progress" class="progress"></div>
</div>

<script>
const baseUrl = window.location.origin;
let allModels=[];

async function loadModelList(){
    const r=await fetch(`${baseUrl}/upscaler_downloader/list`);
    const d=await r.json();
    let html='';
    allModels=d.upscalers||[];
    allModels.forEach(m=>{
        const mb=(m.size/1024/1024).toFixed(2);
        html+=`<div class="model-item"><span>${m.name} (${mb}MB)</span>
        <button class="download-btn" onclick="downloadModel('${encodeURIComponent(m.name)}')">下载</button></div>`;
    });
    document.getElementById('modelList').innerHTML=html||'暂无文件';
}

function downloadModel(name){
    const link=document.createElement('a');
    link.href=`${baseUrl}/upscaler_downloader/download_file/${name}`;
    link.download=name.split('/').pop();
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

document.getElementById('downloadForm').addEventListener('submit',async e=>{
    e.preventDefault();
    const resultDiv=document.getElementById('result');
    const data={
        upscaler_name:upscalerName.value,
        download_url:downloadUrl.value
    };
    const r=await fetch(`${baseUrl}/upscaler_downloader/download`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(data)
    });
    const d=await r.json();
    resultDiv.className=r.ok?'result success':'result error';
    resultDiv.textContent=d.message||d.error;
    resultDiv.style.display='block';
    if(r.ok){document.getElementById('downloadForm').reset();loadModelList();}
});

document.getElementById('refreshBtn').onclick=loadModelList;

document.getElementById('downloadAllBtn').onclick=async ()=>{
    const progressDiv=document.getElementById('progress');
    for(let i=0;i<allModels.length;i++){
        progressDiv.textContent=`正在下载 ${i+1}/${allModels.length}: ${allModels[i].name}`;
        downloadModel(encodeURIComponent(allModels[i].name));
        await new Promise(r=>setTimeout(r,500));
    }
    progressDiv.textContent=`完成！已下载 ${allModels.length} 个文件`;
    setTimeout(()=>{progressDiv.textContent='';},3000);
}

window.onload=loadModelList;
</script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type="text/html")


# ---------------------------------------
# Download existing Upscaler -> send to user
# ---------------------------------------
@PromptServer.instance.routes.get("/upscaler_downloader/download_file/{filename:.+}")
async def download_upscaler_file(request):
    try:
        filename = urllib.parse.unquote(request.match_info["filename"])
        upscaler_directory = folder_paths.get_folder_paths("upscale_models")[0]

        try:
            file_path = safe_join(upscaler_directory, filename)
        except ValueError:
            return web.json_response({"error": "Forbidden"}, status=403)

        if not os.path.exists(file_path):
            return web.json_response({"error": "File not found"}, status=404)

        return web.FileResponse(
            file_path,
            headers={
                "Content-Disposition": f'attachment; filename="{os.path.basename(file_path)}"'
            },
        )

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------
# Node mappings
# ---------------------------------------
NODE_CLASS_MAPPINGS = {
    "UpscalerDownloader": UpscalerDownloader
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "UpscalerDownloader": "Upscaler Downloader"
}
