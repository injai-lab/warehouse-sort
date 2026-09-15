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

공식 소스 커밋 `6048f33217f26ae39009a812f53c81171517f393`을 도입했습니다.
설치 및 검증 상태는 아래 문서를 확인하세요.

- [V100 설치와 실행 명령](docs/SETUP_V100.md)
- [공식 출처·커밋·라이선스 상태](docs/UPSTREAM.md)
- [공식 README 사본](docs/upstream/README.md)
- [공식 학습 안내](il/README.md)
- [공식 제출 안내](SUBMISSION.md)
- [환경 검증 결과](experiments/2026-09-15-setup.md)
- [현재 데이터 접근 상태](experiments/2026-09-15-data-access.md)

시스템 환경은 유지하고 `.venv`만 사용합니다. 데이터와 체크포인트는 Git에 올리지 않습니다.

## Git 관리 범위

코드, 설정 템플릿, 문서, `experiments/`의 요약 기록을 관리합니다.
가상환경, 데이터, 체크포인트, 상세 로그, 인증 파일은 `.gitignore`로 제외합니다.
실험 요약에는 설정, 시드, 코드 커밋, 주요 지표와 로컬 체크포인트 경로를 기록합니다.
