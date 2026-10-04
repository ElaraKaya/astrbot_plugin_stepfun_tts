"""阶跃 StepAudio TTS 插件

参考 AstrBot 官方插件开发文档（docs.astrbot.app/dev/star）实现。
"""

import asyncio
import base64
import pathlib
import uuid

import aiohttp
from pydantic import Field
from pydantic.dataclasses import dataclass

import astrbot.api.message_components as Comp
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.core.agent.run_context import ContextWrapper
from astrbot.core.agent.tool import FunctionTool, ToolExecResult
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

CACHE_DIR = (
    pathlib.Path(get_astrbot_data_path()) / "plugin_data" / "astrbot_plugin_stepfun_tts"
)


async def to_wav(data: bytes, src_fmt: str) -> pathlib.Path:
    """把任意音频格式转成单声道 44.1k wav，供 Record 组件使用。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    src_file = CACHE_DIR / f"{uuid.uuid4().hex}.{src_fmt}"
    out = CACHE_DIR / f"{uuid.uuid4().hex}.wav"
    src_file.write_bytes(data)
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(src_file),
        "-ar",
        "44100",
        "-ac",
        "1",
        str(out),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    src_file.unlink(missing_ok=True)
    if not out.exists():
        raise RuntimeError("ffmpeg 转换失败，请检查音频是否损坏")
    return out


def pick_api_key(conf: dict) -> str:
    """面板里 api_key 是 list 形态，兼容单值和旧版字符串。"""
    raw = conf.get("api_key")
    if isinstance(raw, list):
        raw = next((k for k in raw if str(k or "").strip()), "")
    return str(raw or "").strip()


INSTRUCTION_CHAR_LIMIT = {
    "stepaudio-2.5-tts": 200,
    "stepaudio-3-tts": 500,
}
"""各模型允许的 instruction 字符上限，超出会直接报错。"""


@dataclass
class StepfunSpeechTool(FunctionTool[AstrAgentContext]):
    """把文字转成语音消息。"""

    name: str = "stepfun_speak"
    description: str = (
        "使用阶跃 StepAudio 把文字合成为语音，并以语音消息形式发到当前会话。"
        "适合把旁白、台词、提示语直接念出来。"
        "语气演绎有两层：instruction 控制整段基调，text 里用圆括号 () 插入句内指令"
        "（括号里的内容只当指令，不会被念出来）。"
        "用户没有明确要求语气、情绪或说话方式时，不要传 instruction，留空即使用插件预设语气。"
        "只有用户明确指定与预设不同的语气时才填写。传了会覆盖预设，不会和预设叠加。"
        "instruction 只对 stepaudio-2.5-tts / stepaudio-3-tts 生效，其他模型传了会报错。"
    )
    parameters: dict = Field(
        default_factory=lambda: {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": (
                        "要朗读的文字内容。可以在句中用圆括号插入句内演绎指令，"
                        "如「（压低声音）我没事。（短促吸气）真的。」"
                        "括号里的内容不会被朗读出来。"
                    ),
                },
                "instruction": {
                    "type": "string",
                    "description": (
                        "整段音频的全局语气与演绎指令，用自然语言自由描述，"
                        "如「声音极度紧绷，语速快而断续，带明显的压抑感」"
                        "「语气冰冷，压迫感强，语速偏慢」。"
                        "不要写「用 XX 语气朗读」这类指令式套话，也不要写角色名、"
                        "不要在这里调节速（语速请用 speed 参数）。"
                        "用户没明确要求语气时不要传本参数，留空就用插件预设，不要自己编一条。"
                        "传了非空内容会覆盖预设，不会和预设叠加。"
                        "上限：2.5-tts 200 字，3-tts 500 字，超出报错。"
                    ),
                },
                "speed": {
                    "type": "number",
                    "description": "语速倍率，0.5 慢速，1.0 常速，1.5 快速。",
                },
            },
            "required": ["text"],
        }
    )
    conf: dict = Field(default_factory=dict)

    async def call(
        self, context: ContextWrapper[AstrAgentContext], **kwargs
    ) -> ToolExecResult:
        text = str(kwargs.get("text") or "").strip()
        if not text:
            return "错误：text 参数不能为空。"

        api_key = pick_api_key(self.conf)
        api_base = str(self.conf.get("api_base_url") or "").strip()
        if not api_key or not api_base:
            return "错误：阶跃 TTS 插件尚未配置 api_key 或 api_base。"

        limit = int(self.conf.get("max_char_limit") or 1000)
        if len(text) > limit:
            return f"错误：文本 {len(text)} 字超过单次上限 {limit} 字，请分批朗读。"

        voice = str(self.conf.get("voice") or "livelybreezy-female")
        try:
            speed = float(
                kwargs.get("speed")
                if kwargs.get("speed") is not None
                else self.conf.get("default_speed", 1.0)
            )
        except (TypeError, ValueError):
            speed = float(self.conf.get("default_speed", 1.0))

        body = {
            "model": str(self.conf.get("model") or "stepaudio-2.5-tts"),
            "input": text,
            "voice": voice,
            "response_format": str(self.conf.get("response_format") or "mp3"),
            "speed": speed,
        }
        default_instruction = str(self.conf.get("default_instruction") or "").strip()
        instruction = str(kwargs.get("instruction") or "").strip() or default_instruction
        if instruction:
            cap = INSTRUCTION_CHAR_LIMIT.get(str(body["model"]), 200)
            if len(instruction) > cap:
                return f"错误：instruction {len(instruction)} 字超出 {body['model']} 的 {cap} 字上限，请精简后重试。"
            body["instruction"] = instruction

        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=90))
        try:
            async with session.post(
                f"{api_base.rstrip('/')}/audio/speech",
                json=body,
                headers={"Authorization": f"Bearer {api_key}"},
            ) as resp:
                if resp.status != 200:
                    detail = (await resp.text())[:300]
                    return f"错误：阶跃 TTS 返回 {resp.status}，{detail}"
                data = await resp.read()
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[stepfun_tts] 请求失败: {exc}")
            return f"错误：请求阶跃 TTS 失败，{exc}"
        finally:
            await session.close()

        if not data:
            return "错误：阶跃 TTS 返回了空音频。"

        try:
            if self.conf.get("send_as_voice", True):
                path = await to_wav(data, body["response_format"])
                chain = MessageChain(chain=[Comp.Record(file=str(path), url=str(path))])
            else:
                b64 = base64.b64encode(data).decode()
                chain = MessageChain(
                    chain=[
                        Comp.Plain(f"data:audio/{body['response_format']};base64,{b64}")
                    ]
                )
            await context.context.context.send_message(
                context.context.event.unified_msg_origin, chain
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[stepfun_tts] 发送失败: {exc}")
            return f"错误：发送语音失败，{exc}"

        detail = f"，语气指令：{instruction}" if instruction else ""
        return f"已用 {voice} 朗读 {len(text)} 字并发送语音（语速 {speed}{detail}）。"


@register(
    "astrbot_plugin_stepfun_tts",
    "ElaraKaya",
    "阶跃 StepAudio TTS 语音合成，给 LLM 暴露朗读内容、语速与语气指令",
    "1.0.0",
    "https://github.com/ElaraKaya/astrbot_plugin_stepfun_tts",
)
class StepfunTTSPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.context.add_llm_tools(StepfunSpeechTool(conf=dict(config)))

    @filter.command("tts", alias={"语音", "朗读"})
    async def tts_cmd(self, event, text: str = "", speed: float = 0.0, voice: str = ""):
        """阶跃 TTS 语音合成

        用法: /tts <朗读内容> [语速] [音色]
        """
        api_key = pick_api_key(self.config)
        if not api_key:
            yield event.plain_result("阶跃 TTS 未配置 api_key。")
            return
        target = text.strip()
        if not target:
            yield event.plain_result("用法: /tts <朗读内容> [语速] [音色]")
            return

        api_base = str(self.config.get("api_base_url") or "").strip().rstrip("/")
        fmt = str(self.config.get("response_format") or "mp3")
        body = {
            "model": str(self.config.get("model") or "stepaudio-2.5-tts"),
            "input": target,
            "voice": voice.strip()
            or str(self.config.get("voice") or "livelybreezy-female"),
            "response_format": fmt,
            "speed": speed or float(self.config.get("default_speed") or 1.0),
        }
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=90)
            ) as session:
                async with session.post(
                    f"{api_base}/audio/speech",
                    json=body,
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as resp:
                    if resp.status != 200:
                        detail = (await resp.text())[:300]
                        yield event.plain_result(
                            f"合成失败，返回 {resp.status}：{detail}"
                        )
                        return
                    data = await resp.read()
            if self.config.get("send_as_voice", True):
                path = await to_wav(data, fmt)
                yield event.chain_result([Comp.Record(file=str(path), url=str(path))])
            else:
                b64 = base64.b64encode(data).decode()
                yield event.plain_result(f"data:audio/{fmt};base64,{b64}")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[stepfun_tts] 合成失败: {exc}")
            yield event.plain_result(f"合成失败：{exc}")
