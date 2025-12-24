import { app } from "/scripts/app.js";

// 添加一个菜单项来打开放大模型下载器
app.registerExtension({
    name: "UpscalerDownloader.Extension",
    async setup() {
        // 创建一个新的菜单项
        const menu = document.querySelector(".comfy-menu");
        if (menu) {
            const separator = document.createElement("hr");
            separator.style.margin = "10px 0";
            menu.appendChild(separator);
            
            const button = document.createElement("button");
            button.textContent = "放大模型下载器";
            button.onclick = () => {
                // 打开新的窗口或标签页显示放大模型下载器
                window.open("/upscaler_downloader", "_blank");
            };
            menu.appendChild(button);
        }
    }
});

// 注册静态文件路由
async function registerStaticRoutes() {
    try {
        console.log("Upscaler Downloader extension loaded");
    } catch (error) {
        console.error("Failed to register static routes:", error);
    }
}

registerStaticRoutes();
