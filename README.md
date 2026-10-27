# astrbot_plugin_stepfun_tts

阶跃 StepFun StepAudio TTS 语音合成插件。给 LLM 暴露 `stepfun_speak` 工具，可指定朗读内容、语气指令和语速；也提供 `/tts` 指令手动合成。

灵感来源：AstrBot 官方插件开发文档 https://docs.astrbot.app/dev/star/plugin-new.html

## 功能

- LLM 工具 `stepfun_speak`，参数 `text` / `instruction` / `speed` / `continue_after`
  - 默认语音发送成功后返回空，结束本轮，不再附带文字。想说的都写进 `text`
  - `continue_after` 设为 true 时改为返回一句话，模型可以再来一轮。不传或 false 仍是静默结束
  - `text` 里可用圆括号插入句内演绎指令，如「`（长长地叹了一口气，语气无奈又疲惫）我没事。（短促地吸了一口气，突然压低到极致的气声）真的。`」，括号内容作为导演指令不朗读
  - `instruction` 控制整段全局语气，不传则使用面板里的默认语气
  - `instruction` 字符上限：`stepaudio-2.5-tts` 200 字，`stepaudio-3-tts` 500 字
- 指令 `/tts <朗读内容> [语速] [音色]` 手动合成，音色可临时覆盖面板默认值
- 合成后自动用 ffmpeg 转成单声道 44.1k wav，以语音消息发出

## 句内括号指令与语气调优指南

StepAudio 模型的句内括号 `()` 接收的是**完整的动作加语气描述（导演指令）**，而非拟声词开关：

- **推荐写法（动作 + 情绪状态）**：
  - 叹气/无奈：`（长长地叹了一口气，语气无奈又疲惫）`
  - 笑声/调侃：`（忍不住笑出声，边笑边带着调侃的语气说）`、`（扑哧一声笑出来，语气轻快）`
  - 呼吸/气声：`（短促地吸了一口气，突然压低到极致的气声）`
  - 情绪转折：`（咬牙切齿，声音压得很低）`、`（语气突然软下来，带着一点委屈）`
- **避坑事项**：
  1. **不要塞拟声词**：不要在括号内外写「噗哈哈」「哈哈」「嘻嘻」「哼哼」「噗」等拟声词（写在括号外会被生硬棒读，塞进括号内对克隆音色极易失真或失效）。
  2. **不要连叠括号**：同一处指令请合并在单个括号内（如 `（短促吸气，压低声音）`），连写多个括号容易导致截断吞字。
  3. **括号后直接接台词**：括号后不要紧跟省略号 `……`，也避免在句首无铺垫硬塞笑声。
  4. **全局预设留出动态空间**：`default_instruction` 建议填写「声音自然灵动，语调俏皮有呼吸感，情绪随句内指令明显起伏」，避免锁死「轻声呢喃」等单一低音量描述，否则会压平句内括号的语气反差。

### 官方参考与可查链接

- **StepAudio 3 TTS 官方入口（支持官方音色与克隆音色 `voice` + `instruction` + 句内 `()` 指令）**：
  - 在线语音体验中心（TTS）：https://www.stepfun.com/studio/audio?tab=tts
  - StepAudio 3 TTS 模型文档：https://platform.stepfun.com/docs/zh/guides/models/stepaudio-3-tts
  - 语音合成 API 参考（`/v1/audio/speech`）：https://platform.stepfun.com/docs/zh/api-reference/audio/create-audio
  - 音频合成最佳实践与音色清单：https://platform.stepfun.com/docs/zh/guides/developer/tts
- **StepAudio 2.5 TTS 官方交互式 Demo（含单句多情绪、呼吸、笑声、叹气等完整括号指令示例，与 3-tts 括号语法通用）**：
  - 交互页面：https://stepaudiollm.github.io/step-audio-2.5-tts/zh.html
  - 官方示例文本数据源：https://stepaudiollm.github.io/step-audio-2.5-tts/demo-data.zh.js
  - StepAudio 2.5 TTS 模型文档：https://platform.stepfun.com/docs/zh/guides/models/stepaudio-2.5-tts
- **StepAudio 3 Gen 演示页（注：`stepaudio-3-gen-preview` 走 `/v1/audio/generate`，靠自然语言实时捏音色，不支持传入 `voice` 克隆/预设音色 ID，仅其中的剧本 `()` 括号动作描述可作参考）**：
  - 演示页：https://stepaudiollm.github.io/step-audio-3-gen/
  - StepAudio 3 技术报告：https://arxiv.org/abs/2609.12945

## 配置

在插件配置面板填写：

| 配置项 | 说明 |
| --- | --- |
| `api_key` | 阶跃 API 密钥，列表形式，填一项即可 |
| `api_base_url` | 官方 `https://api.stepfun.com/v1`，国际站 `https://api.stepfun.ai/v1`，Step Plan 订阅 `https://api.stepfun.com/step_plan/v1` |
| `model` | `stepaudio-2.5-tts` 或 `stepaudio-3-tts` |
| `voice` | 阶跃内置或复刻音色 ID，如 `cixingnansheng`、`wenroushunv`、`livelybreezy-female`、`tianfeifei` |
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
