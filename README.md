# WarehouseSort

로봇 택배 색상 분류 대회의 코드와 간결한 실험 기록을 관리합니다.

대회: https://www.kaggle.com/competitions/marso-hack-berlin-2026-robot-parcel-sorting-challenge

## 첫 목표

1. 상태 기반(state) easy 시범 데이터로 기본 Diffusion Policy 학습
2. 저장한 모델을 시뮬레이터에서 평가

## 작업 환경

- 서버: `pepe-student`
- 작업 경로: `/home/student/projects/Robot Parcel Sorting Challenge`
- 전용 Python: `.venv/bin/python` (3.10.21)
- 환경 점검: [ENVIRONMENT.md](ENVIRONMENT.md)

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
source .venv/bin/activate
```

대회 패키지 설치와 데이터 다운로드는 아직 시작하지 않았습니다.
Python 및 PyTorch 조합은 대회 공식 요구사항 확인 후 확정합니다.

## Git 관리 범위

코드, 설정 템플릿, 문서, `experiments/`의 요약 기록을 관리합니다.
가상환경, 데이터, 체크포인트, 상세 로그, 인증 파일은 `.gitignore`로 제외합니다.
실험 요약에는 설정, 시드, 코드 커밋, 주요 지표와 로컬 체크포인트 경로를 기록합니다.
