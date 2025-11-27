#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라벨 파일 변환 스크립트
기존 sprocket 클래스들을 COCO 80개 클래스 뒤에 배치
- 클래스 0 -> 80 (sprocket)
- 클래스 1 -> 81 (sprocket_3)
- 클래스 2 -> 82 (sprocket_db30)
- 클래스 3 -> 83 (sprocket_z36)
"""
import os
from pathlib import Path

DATASET_ROOT = '/Users/goodsee/dongwon/yolo_dataset'
LBL_DIR = os.path.join(DATASET_ROOT, 'train', 'labels')

# 변환 매핑: 기존 클래스 ID -> 새 클래스 ID
CLASS_MAPPING = {
    0: 80,  # sprocket -> 80
    1: 81,  # sprocket 3 -> 81
    2: 82,  # sprocket db30 -> 82
    3: 83,  # sprocket z36 -> 83
}

def convert_label_file(label_path):
    """라벨 파일의 클래스 ID를 변환"""
    with open(label_path, 'r') as f:
        lines = f.readlines()
    
    converted_lines = []
    changed = False
    for line in lines:
        parts = line.strip().split()
        if not parts:
            converted_lines.append(line)
            continue
        
        try:
            old_class_id = int(parts[0])
            if old_class_id in CLASS_MAPPING:
                # 클래스 ID 변환
                parts[0] = str(CLASS_MAPPING[old_class_id])
                converted_lines.append(' '.join(parts) + '\n')
                changed = True
            else:
                # 변환할 필요 없는 클래스는 그대로 유지
                converted_lines.append(line)
        except ValueError:
            # 숫자가 아닌 경우 그대로 유지
            converted_lines.append(line)
    
    if changed:
        with open(label_path, 'w') as f:
            f.writelines(converted_lines)
    
    return changed

def main():
    label_files = list(Path(LBL_DIR).glob('*.txt'))
    print(f"총 {len(label_files)}개의 라벨 파일 발견")
    
    converted_count = 0
    for label_file in label_files:
        if convert_label_file(str(label_file)):
            converted_count += 1
    
    print(f"✅ {converted_count}개의 라벨 파일이 변환되었습니다.")
    print(f"변환 매핑: {CLASS_MAPPING}")
    print("라벨 파일 변환 완료.")

if __name__ == '__main__':
    main()
