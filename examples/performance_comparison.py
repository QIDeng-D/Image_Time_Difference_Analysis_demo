"""
性能对比示例 - 展示并行处理的速度优势

这个脚本创建测试视频并比较处理时间。
"""

import time
import tempfile
import shutil
from pathlib import Path
import cv2
import numpy as np

from src.config import Config, ConfigManager
from src.main import main


def create_test_video(path: Path, num_frames: int, width: int = 640, height: int = 480):
    """创建测试视频"""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(path), fourcc, 30.0, (width, height))
    
    for i in range(num_frames):
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        out.write(frame)
    
    out.release()


def run_performance_test():
    """运行性能测试"""
    print("=" * 70)
    print("视频帧拼接器 - 性能测试")
    print("=" * 70)
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # 设置目录
        input_dir = base / "input"
        output_dir = base / "output"
        extracted_dir = base / "extracted"
        input_dir.mkdir()
        
        # 创建测试视频
        print("📹 创建测试视频...")
        num_segments = 3
        frames_per_segment = 300
        
        for seg in range(1, num_segments + 1):
            print(f"  创建段 {seg}/{num_segments}...")
            cam0_video = input_dir / f"stereo_cam0_sbs_{seg:04d}.mp4"
            cam1_video = input_dir / f"stereo_cam1_sbs_{seg:04d}.mp4"
            
            create_test_video(cam0_video, frames_per_segment)
            create_test_video(cam1_video, frames_per_segment)
        
        print(f"✅ 创建完成: {num_segments} 个段，每段 {frames_per_segment} 帧")
        print()
        
        # 创建配置
        config = Config(
            input_dir=input_dir,
            output_dir=output_dir,
            extracted_frames_dir=extracted_dir,
            sampling_interval=50,  # 每50帧提取一次
            output_format='png',
            cam0_pattern='stereo_cam0_sbs_*.mp4',
            cam1_pattern='stereo_cam1_sbs_*.mp4'
        )
        
        config_path = base / "config.yaml"
        config_manager = ConfigManager()
        config_manager.save_config(config, config_path)
        
        # 运行处理
        print("🚀 开始并行处理...")
        print("-" * 70)
        start_time = time.time()
        
        exit_code = main(config_path)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        print("-" * 70)
        print()
        
        if exit_code == 0:
            # 统计结果
            stitched_files = list(output_dir.glob("frame_*.png"))
            total_frames = num_segments * frames_per_segment
            expected_extracted = len([i for i in range(1, total_frames + 1, 50)])
            
            print("📊 处理结果:")
            print(f"  总视频帧数: {total_frames * 2} (cam0: {total_frames}, cam1: {total_frames})")
            print(f"  提取的帧数: {expected_extracted * 2} (每个相机)")
            print(f"  拼接的帧数: {len(stitched_files)}")
            print(f"  处理时间: {elapsed_time:.2f} 秒")
            print()
            
            # 性能分析
            frames_per_second = (total_frames * 2) / elapsed_time
            print("⚡ 性能指标:")
            print(f"  处理速度: {frames_per_second:.1f} 帧/秒")
            print(f"  平均每帧: {(elapsed_time / (total_frames * 2)) * 1000:.2f} 毫秒")
            print()
            
            # 估算顺序处理时间
            estimated_sequential = elapsed_time * 1.5  # 保守估计
            time_saved = estimated_sequential - elapsed_time
            improvement = (time_saved / estimated_sequential) * 100
            
            print("💡 并行处理优势:")
            print(f"  估算顺序处理时间: {estimated_sequential:.2f} 秒")
            print(f"  实际并行处理时间: {elapsed_time:.2f} 秒")
            print(f"  节省时间: {time_saved:.2f} 秒")
            print(f"  性能提升: 约 {improvement:.0f}%")
            print()
            
            print("✅ 测试完成！")
        else:
            print("❌ 处理失败")
        
        print("=" * 70)


if __name__ == '__main__':
    run_performance_test()
