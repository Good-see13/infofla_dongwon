"""
로깅 설정 모듈
레벨별 폴더 분리 및 자동 삭제 기능
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta
import glob
from dotenv import load_dotenv

load_dotenv()


class LevelFilter(logging.Filter):
    """특정 레벨만 필터링하는 클래스"""
    
    def __init__(self, level):
        super().__init__()
        self.level = level
    
    def filter(self, record):
        return record.levelno == self.level


def cleanup_old_logs(log_dir: str, retention_days: int):
    """
    오래된 로그 파일 삭제
    
    Args:
        log_dir: 로그 디렉토리 경로
        retention_days: 보관 기간 (일)
    """
    if not os.path.exists(log_dir):
        return
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    # 모든 로그 파일 검색
    log_files = glob.glob(os.path.join(log_dir, "*.log*"))
    
    for log_file in log_files:
        try:
            # 파일 수정 시간 확인
            file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            
            if file_mtime < cutoff_date:
                os.remove(log_file)
                print(f"🗑️  Removed old log: {log_file}")
        except Exception as e:
            print("Warning: failed to remove log {0}: {1}".format(log_file, e))


def setup_logging():
    """
    로깅 설정
    
    구조:
    - logs/info/YYYY-MM-DD.log : INFO 레벨 로그
    - logs/error/YYYY-MM-DD.log : ERROR 레벨 로그
    
    환경 변수:
    - LOG_RETENTION_DAYS: 로그 보관 기간 (기본값: 30일)
    """
    
    # 환경 변수에서 보관 기간 가져오기
    retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    
    # 로그 디렉토리 생성
    log_base_dir = "logs"
    info_log_dir = os.path.join(log_base_dir, "info")
    error_log_dir = os.path.join(log_base_dir, "error")
    
    Path(info_log_dir).mkdir(parents=True, exist_ok=True)
    Path(error_log_dir).mkdir(parents=True, exist_ok=True)
    
    # 오래된 로그 파일 삭제
    cleanup_old_logs(info_log_dir, retention_days)
    cleanup_old_logs(error_log_dir, retention_days)
    
    # 로그 포맷 (밀리초 제거)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'  # 밀리초 없는 포맷
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 1. 콘솔 핸들러 (모든 레벨)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # 2. INFO 레벨 파일 핸들러
    info_handler = TimedRotatingFileHandler(
        filename=os.path.join(info_log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log"),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(LevelFilter(logging.INFO))
    info_formatter = logging.Formatter(log_format, date_format)
    info_handler.setFormatter(info_formatter)
    root_logger.addHandler(info_handler)
    
    # 3. WARNING 레벨도 INFO 폴더에 저장
    warning_handler = TimedRotatingFileHandler(
        filename=os.path.join(info_log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log"),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.addFilter(LevelFilter(logging.WARNING))
    warning_formatter = logging.Formatter(log_format, date_format)
    warning_handler.setFormatter(warning_formatter)
    root_logger.addHandler(warning_handler)
    
    # 4. ERROR 레벨 파일 핸들러
    error_handler = TimedRotatingFileHandler(
        filename=os.path.join(error_log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log"),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(log_format, date_format)
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # 5. CRITICAL 레벨도 ERROR 폴더에 저장
    critical_handler = TimedRotatingFileHandler(
        filename=os.path.join(error_log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log"),
        when='midnight',
        interval=1,
        backupCount=retention_days,
        encoding='utf-8'
    )
    critical_handler.setLevel(logging.CRITICAL)
    critical_formatter = logging.Formatter(log_format, date_format)
    critical_handler.setFormatter(critical_formatter)
    root_logger.addHandler(critical_handler)
    
    # SQLAlchemy 로거 비활성화 (쿼리 출력 제거)
    for logger_name in ['sqlalchemy.engine', 'sqlalchemy.pool', 'sqlalchemy.orm']:
        sa_logger = logging.getLogger(logger_name)
        sa_logger.setLevel(logging.WARNING)  # INFO 로그 출력 안함
        sa_logger.handlers.clear()
        sa_logger.propagate = True
    
    # 로거 반환
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging initialized - Retention: {retention_days} days")
    logger.info(f"📂 INFO logs: {info_log_dir}")
    logger.info(f"📂 ERROR logs: {error_log_dir}")
    
    return logger


if __name__ == "__main__":
    # 테스트
    logger = setup_logging()
    
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")
