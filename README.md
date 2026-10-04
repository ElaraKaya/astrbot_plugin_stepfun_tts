# astrbot_plugin_stepfun_tts

阶跃 StepFun StepAudio TTS 语音合成插件。给 LLM 暴露 `stepfun_speak` 工具，可指定朗读内容、语气指令和语速；也提供 `/tts` 指令手动合成。

灵感来源：AstrBot 官方插件开发文档 https://docs.astrbot.app/dev/star/plugin-new.html

## 功能

- LLM 工具 `stepfun_speak`，参数 `text` / `instruction` / `speed`
  - `text` 里可用圆括号插入句内演绎指令，如「（压低声音）我没事。」括号内容不朗读
  - `instruction` 控制整段全局语气，不传则使用面板里的默认语气
  - `instruction` 字符上限：`stepaudio-2.5-tts` 200 字，`stepaudio-3-tts` 500 字
- 指令 `/tts <朗读内容> [语速] [音色]` 手动合成，音色可临时覆盖面板默认值
- 合成后自动用 ffmpeg 转成单声道 44.1k wav，以语音消息发出

## 配置

在插件配置面板填写：

| 配置项 | 说明 |
| --- | --- |
| `api_key` | 阶跃 API 密钥，列表形式，填一项即可 |
| `api_base_url` | 官方 `https://api.stepfun.com/v1`，国际站 `https://api.stepfun.ai/v1`，Step Plan 订阅 `https://api.stepfun.com/step_plan/v1` |
| `model` | `stepaudio-2.5-tts` 或 `stepaudio-3-tts` |
| `voice` | 阶跃内置音色 ID，如 `cixingnansheng`、`wenroushunv`、`livelybreezy-female`、`tianfeifei` |
| `default_instruction` | 默认语气指令，仅在 LLM 未传 `instruction` 时生效 |
| `default_speed` | 默认语速，1.0 为常速 |
| `response_format` | `mp3` / `wav` / `pcm` |
| `send_as_voice` | 开启则转 wav 作为语音条发送，关闭则发送音频文件 |

模型与渠道的对应关系：`stepaudio-3-tts` 只能走直接调用 API，Step Plan 通道只有 `stepaudio-2.5-tts`。

## 依赖

需要系统装有 `ffmpeg`，用于把音频转成语音消息可用的 wav。

## 安装

把插件目录放进 `AstrBot/data/plugins/`，或在 WebUI 插件市场安装后在面板重载。

## 许可证

MIT
