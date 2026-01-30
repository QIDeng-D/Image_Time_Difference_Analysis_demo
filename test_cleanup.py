"""测试多进程清理是否正常工作"""

import sys
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_cleanup():
    """测试程序是否能正常退出"""
    logger.info("="*80)
    logger.info("开始测试多进程清理...")
    logger.info("="*80)
    
    start_time = time.time()
    
    try:
        # 导入主程序
        from src.main import main
        
        # 运行主程序
        logger.info("运行主程序...")
        exit_code = main(Path('config.yaml'))
        
        elapsed = time.time() - start_time
        
        logger.info("="*80)
        if exit_code == 0:
            logger.info(f"✅ 测试成功！程序正常退出")
            logger.info(f"   退出码: {exit_code}")
            logger.info(f"   总耗时: {elapsed:.2f}秒")
        else:
            logger.error(f"❌ 测试失败！退出码: {exit_code}")
        logger.info("="*80)
        
        return exit_code
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        logger.info("="*80)
        logger.info(f"⚠️ 用户中断测试 (耗时: {elapsed:.2f}秒)")
        logger.info("="*80)
        return 1
        
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("="*80)
        logger.error(f"❌ 测试出错: {e}")
        logger.error(f"   耗时: {elapsed:.2f}秒")
        logger.error("="*80)
        return 1

if __name__ == '__main__':
    logger.info("\n" + "="*80)
    logger.info("多进程清理测试 (Multiprocess Cleanup Test)")
    logger.info("="*80)
    logger.info("说明:")
    logger.info("  - 如果程序在完成后5秒内退出 = ✅ 清理成功")
    logger.info("  - 如果程序挂起不退出 = ❌ 清理失败")
    logger.info("  - 按 Ctrl+C 可以测试中断处理")
    logger.info("="*80 + "\n")
    
    exit_code = test_cleanup()
    
    logger.info("\n" + "="*80)
    logger.info("测试完成！")
    logger.info("="*80)
    
    sys.exit(exit_code)
