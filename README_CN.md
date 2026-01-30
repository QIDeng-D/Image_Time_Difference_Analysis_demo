# 视频帧拼接工具 (Video Frame Stitcher)

一个用于处理分段立体相机视频的 Python 应用程序，可以按可配置的间隔提取帧，并将两个相机的对应帧垂直拼接成统一的输出图像。

## ✨ 主要特性

- **自动视频发现**：自动扫描输入目录中匹配相机命名模式的视频文件
- **并行帧提取**：同时从 cam0 和 cam1 提取帧，实现最高效率 ⚡
- **可配置帧采样**：按固定间隔提取帧（例如每 100 帧提取一次）
- **跨段连续编号**：在所有视频段中保持连续的帧编号
- **垂直帧拼接**：将两个相机的对应帧组合（cam0 在上，cam1 在下）
- **宽度不匹配处理**：自动处理不同宽度的帧，通过居中对齐
- **实时进度报告**：处理过程中显示进度信息
- **全面错误处理**：优雅的错误处理，提供清晰的错误消息
- **灵活配置**：基于 YAML 的配置，易于自定义
- **详细处理报告**：自动生成包含统计信息的处理报告

## 📋 系统要求

- Python 3.8 或更高版本
- pip 包管理器

## 🚀 安装

### 克隆仓库

```bash
git clone https://github.com/yourusername/video-frame-stitcher.git
cd video-frame-stitcher
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 📖 使用方法

### 基本使用

1. **准备视频文件**：将立体相机视频段放入输入目录。视频应遵循以下命名模式：
   - 相机 0：`stereo_cam0_sbs_0001.mp4`、`stereo_cam0_sbs_0002.mp4` 等
   - 相机 1：`stereo_cam1_sbs_0001.mp4`、`stereo_cam1_sbs_0002.mp4` 等

2. **运行应用程序**：
   ```bash
   python -m src.main
   ```

   这将使用默认的 `config.yaml` 文件。如果不存在，将创建默认配置。

3. **查看输出**：拼接后的帧将保存在配置中指定的输出目录中。

### 使用自定义配置文件

```bash
python -m src.main --config my_config.yaml
```

### 命令行选项

```bash
python -m src.main --help
```

选项：
- `--config`, `-c`：配置文件路径（默认：config.yaml）
- `--version`, `-v`：显示版本信息
- `--help`, `-h`：显示帮助信息

## ⚙️ 配置

应用程序使用 YAML 配置文件。以下是包含所有可用选项的示例：

```yaml
# 包含输入视频段的目录
input_dir: "./segments"

# 拼接输出帧的目录
output_dir: "./stitched_frames"

# 中间提取帧的目录
extracted_frames_dir: "./extracted_frames"

# 每个提取帧之间的帧数（例如 100 表示每 100 帧提取一次）
sampling_interval: 100

# 输出图像格式：'png' 或 'jpg'
output_format: "png"

# 相机 0 视频文件的 glob 模式
cam0_pattern: "stereo_cam0_sbs_*.mp4"

# 相机 1 视频文件的 glob 模式
cam1_pattern: "stereo_cam1_sbs_*.mp4"

# 帧数差异验证阈值（百分比）
frame_count_threshold: 5.0

# 启用帧号叠加
enable_frame_overlay: false

# 叠加字体大小
overlay_font_size: 30

# 叠加位置：'top-left', 'top-right', 'bottom-left', 'bottom-right'
overlay_position: "top-left"
```

### 配置选项说明

| 选项 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `input_dir` | 字符串 | `./segments` | 包含输入视频段的目录 |
| `output_dir` | 字符串 | `./stitched_frames` | 拼接输出帧的目录 |
| `extracted_frames_dir` | 字符串 | `./extracted_frames` | 中间提取帧的目录 |
| `sampling_interval` | 整数 | `100` | 每个提取帧之间的帧数 |
| `output_format` | 字符串 | `png` | 输出图像格式（`png` 或 `jpg`） |
| `cam0_pattern` | 字符串 | `stereo_cam0_sbs_*.mp4` | 相机 0 视频文件的 glob 模式 |
| `cam1_pattern` | 字符串 | `stereo_cam1_sbs_*.mp4` | 相机 1 视频文件的 glob 模式 |
| `frame_count_threshold` | 浮点数 | `5.0` | 帧数差异验证阈值（百分比） |
| `enable_frame_overlay` | 布尔值 | `false` | 是否在帧上叠加帧号 |
| `overlay_font_size` | 整数 | `30` | 叠加文字的字体大小 |
| `overlay_position` | 字符串 | `top-left` | 叠加位置 |

## 📁 目录结构

### 输入结构

```
segments/
├── stereo_cam0_sbs_0001.mp4
├── stereo_cam0_sbs_0002.mp4
├── stereo_cam0_sbs_0003.mp4
├── stereo_cam1_sbs_0001.mp4
├── stereo_cam1_sbs_0002.mp4
└── stereo_cam1_sbs_0003.mp4
```

### 输出结构

```
extracted_frames/
├── cam0/
│   ├── frame_0001.png
│   ├── frame_0101.png
│   └── frame_0201.png
└── cam1/
    ├── frame_0001.png
    ├── frame_0101.png
    └── frame_0201.png

stitched_frames/
├── frame_0001.png
├── frame_0101.png
└── frame_0201.png

processing_report.txt  # 自动生成的处理报告
```

## 🔧 工作原理

1. **视频发现**：应用程序扫描输入目录中匹配配置模式的视频文件，并按相机分组。

2. **并行帧提取**：使用多线程同时从 cam0 和 cam1 提取帧，实现最高效率。帧编号在所有视频段中连续。

3. **帧拼接**：两个相机完成提取后，将对应的帧（具有匹配帧号）垂直拼接在一起，cam0 在上，cam1 在下。

4. **输出**：拼接后的帧保存到输出目录，帧号使用零填充以便正确排序。

5. **生成报告**：自动生成详细的处理报告，包含帧数统计、同步质量等信息。

### 性能优势

通过并行处理，应用程序可以同时处理两个相机：
- **顺序处理**：时间(cam0) + 时间(cam1) + 时间(拼接)
- **并行处理**：max(时间(cam0), 时间(cam1)) + 时间(拼接)
- **速度提升**：帧提取速度提升高达 **2 倍**！🚀

## 💡 使用示例

### 示例 1：每 50 帧提取一次

```yaml
sampling_interval: 50
```

对于 3 个视频段，每个 100 帧（总共 300 帧），将在以下位置提取帧：1、51、101、151、201、251。

### 示例 2：提取每一帧

```yaml
sampling_interval: 1
```

这将从所有视频段中提取每一帧。

### 示例 3：自定义相机模式

```yaml
cam0_pattern: "camera_left_*.avi"
cam1_pattern: "camera_right_*.avi"
```

这允许您处理具有不同命名约定的视频。

### 示例 4：启用帧号叠加

```yaml
enable_frame_overlay: true
overlay_font_size: 40
overlay_position: "top-right"
```

这将在每个拼接帧的右上角显示帧号。

## 🛠️ 错误处理

应用程序优雅地处理各种错误情况：

- **缺少输入目录**：显示错误并终止
- **未找到视频文件**：显示错误并终止
- **损坏的视频文件**：记录错误并跳过该段
- **缺少段对**：记录警告并继续处理可用段
- **帧提取失败**：记录错误并继续下一帧
- **输出目录创建失败**：显示错误并终止
- **帧数差异过大**：提示用户确认是否继续

所有错误都包含描述性消息，指示失败的操作和涉及的特定文件或资源。

## 🧪 测试

项目包含全面的单元测试、基于属性的测试和集成测试。

### 运行所有测试

```bash
pytest tests/
```

### 运行特定测试类别

```bash
# 仅单元测试
pytest tests/ -k "not property"

# 仅基于属性的测试
pytest tests/ -k "property"

# 仅集成测试
pytest tests/test_integration.py
```

### 运行测试并生成覆盖率报告

```bash
pytest tests/ --cov=src --cov-report=html
```

## 📦 支持的视频格式

- MP4 (`.mp4`)
- AVI (`.avi`)

## 📚 依赖项

- Python 3.8+
- opencv-python >= 4.8.0
- Pillow >= 10.0.0
- PyYAML >= 6.0
- hypothesis >= 6.82.0（用于测试）
- pytest >= 7.4.0（用于测试）

## ❓ 故障排除

### 问题："未找到视频文件"

**解决方案**：检查：
- 视频文件是否在正确的输入目录中
- 文件命名模式是否与配置的 `cam0_pattern` 和 `cam1_pattern` 匹配
- 视频文件是否具有正确的扩展名（`.mp4` 或 `.avi`）

### 问题："无法拼接帧：需要两个相机的帧"

**解决方案**：确保：
- 两个相机（cam0 和 cam1）都有视频文件
- 视频文件未损坏
- 视频包含帧（非空）

### 问题：拼接帧的尺寸不正确

**解决方案**：当帧具有不同宽度时，这是预期行为。应用程序通过在背景上居中较窄的帧来自动处理宽度不匹配。如果不希望这样，请确保源视频具有相同的尺寸。

### 问题：帧数差异过大

**解决方案**：
- 检查两个相机的视频是否正确同步
- 调整配置中的 `frame_count_threshold` 值
- 应用程序会提示您确认是否继续处理

## 📄 许可证

本项目按原样提供，用于教育和研究目的。

## 🤝 贡献

欢迎贡献！提交拉取请求之前，请确保所有测试通过。

## 📌 版本

当前版本：1.0.0

## 📧 联系方式

如有问题或疑问，请在项目仓库中提交 issue。

## 🙏 致谢

感谢所有为此项目做出贡献的开发者。
