from app.utils.helper import show_json
from fastapi import Request, UploadFile
import io
from PIL import Image
from app.api.url_check import ALLOWED_MIME, MAX_SIZE, _infer,_extract_middle_frame

# 仅用于将 PIL 的格式名映射到标准 MIME（以实际解码结果为准）
FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "BMP": "image/bmp",
    "WEBP": "image/webp",
}

class UploadCheckHandler:
    # 新增：通用关闭与推理辅助
    async def _safe_close(self, upload: UploadFile):
        try:
            await upload.close()
        except Exception:
            try:
                upload.file.close()
            except Exception:
                pass

    async def _infer_bytes(self, data: bytes):
        if not data:
            return show_json(-1000, "Empty upload.")
        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        image = None
        try:
            image = Image.open(io.BytesIO(data))
            orig_fmt = getattr(image, "format", None)
            image = _extract_middle_frame(image)
            # 回退获取原始格式，避免 GIF 中间帧 convert 后 format 丢失
            info_fmt = None
            try:
                info_fmt = image.info.get("orig_format")
            except Exception:
                pass
            fmt = getattr(image, "format", None) or getattr(image, "_orig_format", None) or info_fmt or orig_fmt
            detected_mime = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "BMP": "image/bmp",
                "WEBP": "image/webp",
                "GIF": "image/gif",
            }.get(fmt or "", "")
            # print(f"Detected image format (after={fmt}, original={orig_fmt}), MIME: {detected_mime}")
            if detected_mime not in ALLOWED_MIME:
                return show_json(-1000, f"Unsupported file type: {detected_mime or 'unknown'}, only jpg/png/bmp/webp/gif allowed.")
            result, err = _infer(image)
        except Exception:
            return show_json(-1000, "Image parsing failed.")
        finally:
            try:
                if image is not None:
                    image.close()
            except Exception:
                pass

        if err:
            return show_json(-1000, err)
        return show_json(200, "success", result)

    async def check(self, request: Request, file: UploadFile):
        # 1) 头部大小预检（快速拒绝；multipart 开销可能导致略大于真实文件）
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_SIZE:
                    return show_json(-1000, "File too large (>10MB), refusing to process.")
            except ValueError:
                pass

        # 2) 读取文件（限流 MAX_SIZE+1）
        try:
            data = await file.read(MAX_SIZE + 1)
        except Exception:
            await self._safe_close(file)
            return show_json(-1000, "Read uploaded file failed.")
        finally:
            await self._safe_close(file)

        if len(data) > MAX_SIZE:
            return show_json(-1000, "File too large (>10MB), refusing to process.")

        # 3) 解码+真实 MIME 校验 + 推理
        return await self._infer_bytes(data)