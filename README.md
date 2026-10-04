# astrbot_plugin_stepfun_tts

阶跃 StepAudio TTS 语音合成插件，为 LLM 暴露朗读内容、语速和语气指令参数。

这是一个 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 插件。

## 功能

- 调用阶跃 StepAudio TTS 接口合成语音（mp3 / wav / pcm）。
- 向 LLM 暴露工具参数：朗读文本、语速、语气指令。
- 可配置：API 密钥、API 基础 URL（支持反代）、模型、音色、默认语气指令、默认语速、输出格式、单次最大字符数、以语音条形式发送。

## 安装

在 AstrBot 插件市场搜索 `astrbot_plugin_stepfun_tts`，或克隆本仓库到 `data/plugins/` 目录下。

## 配置

在 AstrBot 的插件配置面板中填写阶跃 API 密钥（形如 `stp_xxxxx`）。API 密钥保存在本地 `*_config.json` 中，该文件已被 `.gitignore` 排除，不会提交到仓库。

## 使用

在对话中让 LLM 朗读一段内容即可，可附带语速与语气指令。

## 许可证

见仓库说明。
