# YOLO 모델 학습 가이드

이 폴더는 YOLO 모델 학습을 위한 데이터셋과 학습 스크립트를 포함합니다.

## 📁 폴더 구조

```
yolo_dataset/
├── train/
│   ├── images/          # 학습 이미지
│   └── labels/          # YOLO 형식 라벨 (.txt)
├── splits/              # train/val 분할 리스트
│   ├── train.txt
│   └── val.txt
├── data.yaml            # 데이터셋 설정 파일
├── train.ipynb         # 학습 노트북
└── runs/               # 학습 결과 (자동 생성)
    └── detect/
        └── train/
            └── weights/
                ├── best.pt    # 최고 성능 모델
                └── last.pt    # 마지막 epoch 모델
```

## 🚀 초기 학습

### 1. 데이터 준비
- `train/images/`: 학습 이미지 파일
- `train/labels/`: YOLO 형식 라벨 파일 (이미지와 동일한 이름, .txt 확장자)

### 2. 학습 실행
Jupyter Notebook에서 `train.ipynb` 실행:

```python
# 노트북이 자동으로:
# 1. 데이터셋 분할 (train/val)
# 2. data.yaml 업데이트
# 3. 모델 로드 (YOLOv12 → YOLOv10 → YOLOv8 순서로 시도)
# 4. 학습 시작
```

### 3. 학습 설정

**중요 설정:**
- `pretrained=True`: 백본의 사전 학습 가중치 유지 (다른 객체와 구분 가능)
- `lr0=0.001`: 작은 LR로 미세튜닝 (백본이 망가지지 않도록)
- `epochs=50`: 학습 epoch 수
- `device='cpu'`: GPU 사용 시 `'cuda'` 또는 `0`으로 변경

**기본 설정:**
```python
train_kwargs = dict(
    data=DATA_YAML,
    epochs=50,
    patience=20,
    pretrained=True,   # ✅ 백본의 사전 학습 가중치 유지 (중요!)
    lr0=0.001,         # 작은 LR로 미세튜닝
    lrf=0.01,
    batch=16,
    imgsz=640,
    device='cpu',      # GPU 있으면 'cuda' 또는 0
    seed=42,
)
```

## 🔄 추가 학습 (Continual Learning)

**처음부터 다시 학습할 필요 없습니다!** 기존 모델에서 이어서 학습할 수 있습니다.

### 방법 1: Resume 학습 (이어서 학습)

같은 데이터셋으로 더 학습하고 싶을 때:

```python
from ultralytics import YOLO

# 마지막 체크포인트에서 이어서 학습
model = YOLO('runs/detect/train/weights/last.pt')
# 또는 최고 성능 모델에서
# model = YOLO('runs/detect/train/weights/best.pt')

results = model.train(
    data=DATA_YAML,
    epochs=100,        # 총 epoch (이미 50 했으면 50 더 = 총 100)
    resume=True,       # ✅ 이어서 학습
    # 나머지 설정은 동일
)
```

### 방법 2: Transfer Learning (전이 학습)

새로운 데이터셋으로 추가 학습할 때:

```python
from ultralytics import YOLO

# 기존 학습된 모델 로드
model = YOLO('runs/detect/train/weights/best.pt')

# 새로운 데이터로 학습
results = model.train(
    data=NEW_DATA_YAML,  # 새로운 데이터셋
    epochs=50,
    pretrained=False,    # 이미 학습된 모델이므로 False
    lr0=0.001,          # 작은 LR로 미세 조정
    # 나머지 설정 동일
)
```

### 방법 3: Fine-tuning (미세 조정)

기존 모델을 더 정밀하게 조정할 때:

```python
from ultralytics import YOLO

model = YOLO('runs/detect/train/weights/best.pt')

results = model.train(
    data=DATA_YAML,
    epochs=20,
    lr0=0.0001,         # 더 작은 LR로 미세 조정
    pretrained=False,
    # 나머지 설정 동일
)
```

## 📊 학습 결과 확인

학습 완료 후 결과는 `runs/detect/train/` 폴더에 저장됩니다:

- `weights/best.pt`: 최고 성능 모델 (mAP 기준)
- `weights/last.pt`: 마지막 epoch 모델
- `results.png`: 학습 곡선 (loss, mAP 등)
- `confusion_matrix.png`: 혼동 행렬

## ⚙️ 주요 설정 설명

### pretrained=True (중요!)
- **백본의 COCO 사전 학습 가중치를 유지**
- 다른 객체와 sprocket을 구분할 수 있음
- `pretrained=False`로 하면 모든 것을 sprocket으로 인식하는 문제 발생 가능

### Learning Rate
- `lr0=0.001`: 초기 학습률 (백본이 망가지지 않도록 작게 설정)
- `lrf=0.01`: 최종 학습률 비율 (lr0의 1%까지 감소)

### Device 설정
- CPU: `device='cpu'` (느리지만 메모리 적음)
- GPU: `device='cuda'` 또는 `device=0` (빠르지만 메모리 많음)

## 🎯 학습 팁

1. **데이터 증강**: 기본적으로 활성화되어 있음 (mosaic, flip 등)
2. **Early Stopping**: `patience=20`으로 설정되어 있어 개선이 없으면 자동 중단
3. **체크포인트**: `save_period=10`으로 10 epoch마다 저장
4. **Validation**: `test_size=0.01`로 설정 (데이터의 1%를 validation으로 사용)

## ⚠️ 주의사항

- **pretrained=True 필수**: 백본 가중치를 유지하지 않으면 다른 객체와 구분 불가
- **작은 LR 사용**: 큰 LR로 학습하면 기존 가중치가 망가질 수 있음
- **충분한 데이터**: 최소 100개 이상의 이미지 권장
- **라벨 품질**: 정확한 라벨링이 중요함

## 📝 학습 로그 확인

학습 중 실시간으로 다음 정보가 출력됩니다:
- Epoch 진행 상황
- Loss (box_loss, cls_loss, dfl_loss)
- mAP (mAP50, mAP50-95)
- Validation 결과

## 🔍 문제 해결

### 모든 것을 sprocket으로 인식하는 경우
- `pretrained=True` 확인
- `lr0`를 더 작게 (0.0005 등)
- 데이터셋에 negative samples 추가

### 학습이 너무 느린 경우
- GPU 사용 (`device='cuda'`)
- `batch` 크기 증가 (메모리 허용 시)
- `workers` 수 증가

### 메모리 부족 오류
- `batch` 크기 감소
- `imgsz` 크기 감소 (640 → 416)
- `cache=False`로 설정

