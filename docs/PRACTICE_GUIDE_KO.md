# WarehouseSort easy/state 실습 안내

현재 서버에 설치되고 검증된 프로젝트 기준 안내입니다. 이 문서를 작성하면서 새 학습은 실행하지 않았습니다.

## 1. 무엇을 만드는 프로젝트인가

로봇 팔이 택배의 색상을 보고 같은 색상의 분류함으로 옮기도록 행동 모델을 학습합니다.
현재 사용하는 **state 방식**에서는 카메라 사진 대신 시뮬레이터가 알려주는 로봇 관절, 물체 위치, 색상 등의 숫자를 입력합니다.
**easy**는 택배 2개와 고정된 배치를 사용하는 난이도입니다.

전체 흐름은 다음과 같습니다.

```text
시범 데이터: 관측 상태 + 시범 행동
    ↓ 학습
Diffusion Policy 모델
    ↓ 체크포인트 .pt 저장
저장한 모델을 로더로 재구성
    ↓ 현재 상태 → 다음 행동 → 시뮬레이터 상태 변화 반복
분류 정확도와 에피소드 성공률 측정
```

이것은 **모방학습**입니다. 시범 행동에 노이즈를 넣고 그 노이즈를 예측하는 방법으로 행동을 학습합니다.
추론 때는 무작위 행동 배열에서 노이즈를 여러 번 제거해 현재 상태에 맞는 행동을 만듭니다.
시뮬레이터의 보상을 직접 최대화하는 강화학습과 학습 과정이 다릅니다.
학습 중 시뮬레이터를 돌리는 것은 주로 중간 성능 평가를 위해서입니다.

## 2. 가장 먼저 볼 파일

모든 경로는 프로젝트 루트 기준입니다.

| 파일 | 역할 | 실습에서 할 일 |
|---|---|---|
| `scripts/run_v100.sh` | 전용 Python, GPU 번호, 로컬 공유 라이브러리를 설정하는 실행기 | 모든 학습·시뮬레이터 명령 앞에 사용 |
| `il/train.py` | 설정을 읽고 실제 학습 프로그램을 실행하는 입구 | 학습 실행 명령에서 사용 |
| `il/conf/train.yaml` | 환경, 데이터 폴더, 제어 방식 등 학습 공통 설정 | 처음에는 `demo_dir=easy` 유지 |
| `il/conf/method/dp.yaml` | 반복 수, 배치 크기, horizon, 평가 주기 등 DP 설정 | **첫 번째 실습 대상**. 우선 명령줄에서 값 변경 |
| `il/baselines/diffusion_policy/train.py` | 데이터 윈도 구성, 모델, 손실, 최적화, 중간 평가, 저장 | 학습 내부를 이해하거나 알고리즘을 바꿀 때 읽기 |
| `eval.py` | 저장한 모델의 독립 시뮬레이터 평가 | **학습 다음에 실행할 입구** |
| `warehouse_sort/il_policy.py` | 체크포인트 로딩과 실제 행동 생성 | 추론 방식 실험, 모델 구조 변경 시 확인 |
| `conf/config.yaml` | 평가 공통 설정 | 환경 수, 시드, 렌더링 설정 확인 |
| `conf/eval/*.yaml` | 평가 에피소드 수와 환경 시드 | 개발용·최종 평가용 시드 관리 |
| `conf/difficulty/easy.yaml` | 택배 개수와 배치 등 easy 문제 설정 | 환경 실험 단계에서 확인 |
| `warehouse_sort/env.py` | 로봇·택배·분류함 생성, 상태, 보상, 성공 판정 | **문제 자체를 바꾸는 파일**. 첫 학습 실습에서는 유지 |
| `warehouse_sort/utils.py` | 환경 생성, rollout, 지표 집계 등 공통 기능 | 평가 동작을 추적할 때 읽기 |
| `il/baselines/diffusion_policy/diffusion_policy/conditional_unet1d.py` | 노이즈 예측 신경망 | 신경망 구조를 연구할 때 수정 |
| `experiments/` | Git으로 관리하는 설정·성능 요약 | 실험 후 결과 기록 |

처음 읽는 순서: `il/conf/method/dp.yaml` → `il/train.py` → 실제 baseline `train.py` → `eval.py` → `warehouse_sort/il_policy.py`.
`SUBMISSION.md`는 제출 안내이므로 현재 개인 학습 실습의 실행 진입점은 아닙니다.

## 3. 데이터와 용어

데이터 위치:

```text
il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.h5
il/demos/easy/trajectory.state.pd_ee_delta_pos.physx_cuda.json
```

- H5: 실제 상태·행동 배열. JSON: 에피소드, 시드, 환경 등의 메타데이터.
- 전체 **200개 시범**, 시범당 115개 행동, 총 **23,000개 상태 전이**.
- easy 상태 입력은 **54차원**, 행동은 **4차원**: 손끝의 XYZ 이동량과 그리퍼 명령.
- 시범 하나의 관측 배열은 `(116, 54)`, 행동 배열은 `(115, 4)`입니다. 마지막 행동 이후 상태가 하나 더 있습니다.
- 학습기는 시범을 시간 구간으로 잘라 사용합니다. 현재 전체 데이터 설정에서 22,800개 학습 구간이 만들어집니다.
- **iteration/update**: 배치 하나로 모델 가중치를 한 번 갱신하는 것. 30,000회는 시범 30,000개라는 뜻이 아닙니다.
- **batch_size**: 한 번 갱신할 때 사용하는 학습 구간 수.
- **episode**: 시뮬레이터를 초기화하고 로봇이 한 번 작업하는 과정.
- **num_envs**: 동시에 돌리는 시뮬레이터 개수. GPU 개수가 아닙니다. GPU 한 대에서도 여러 환경을 돌립니다.

데이터는 이미 설치되어 있습니다. 기본 실습에 재다운로드나 패키지 재설치는 필요하지 않습니다.

## 4. 실행 환경

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
source .venv/bin/activate
nvidia-smi
scripts/run_v100.sh scripts/smoke_runtime.py cuda
scripts/run_v100.sh scripts/smoke_runtime.py state
```

환경: V100 32GB, Python 3.10.21, PyTorch 2.7.1+cu126, ManiSkill 3.0.1, SAPIEN 3.0.3.
`scripts/run_v100.sh`는 `.venv/bin/python`을 직접 사용하므로 activation 없이도 실행됩니다.
동시에 프로젝트 안에 설치한 공유 라이브러리 경로를 설정합니다. 단순 `python` 실행과 이 점이 다릅니다.

GPU 선택은 `WAREHOUSE_GPU=0 scripts/run_v100.sh ...`처럼 합니다. 현재 기본값도 0입니다.
실행 전에 `nvidia-smi`로 사용 상황을 확인해 사용 가능한 한 대를 선택하세요.
Vulkan 영상 문제는 [별도 기록](VULKAN_TODO.md)에 있습니다. 이번 실습은 항상 영상 없이 진행합니다.

## 5. 직접 해보기: 작은 실험 하나 만들기

아래는 **새로 실행할 때 사용할 예제**입니다. 여기서 안내만 작성했으며 실행하지 않았습니다.
20개 시범, 1,000회 갱신으로 실행 과정을 익힙니다. 성능 비교용 본학습 결과로 해석하지 마세요.
현재 학습기의 learning-rate warmup은 500회이므로 아주 짧은 학습은 특히 실행 확인 목적입니다.

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
EXP_NAME="easy_practice_$(date -u +%Y%m%dT%H%M%SZ)"

if [ -e "il/baselines/diffusion_policy/runs/$EXP_NAME" ]; then
  echo "이미 존재하는 실험입니다. EXP_NAME을 바꾸세요."
else
  WAREHOUSE_GPU=0 scripts/run_v100.sh il/train.py method=dp demo_dir=easy \
    +flags.num_demos=20 flags.total_iters=1000 flags.batch_size=64 \
    flags.num_eval_envs=2 flags.num_eval_episodes=4 \
    flags.eval_freq=500 flags.save_freq=500 flags.log_freq=100 \
    flags.capture_video=false +flags.render_backend=none \
    flags.exp_name="$EXP_NAME"
fi
```

같은 터미널에서 `echo "$EXP_NAME"`으로 실험 이름을 확인할 수 있습니다. 새 터미널에서는 해당 이름을 다시 설정해야 합니다.
학습 명령은 완료될 때까지 터미널을 점유합니다. `Ctrl+C`로 학습을 중단하면 마지막 저장 단계가 실행되지 않을 수 있습니다.

결과 폴더:

```text
il/baselines/diffusion_policy/runs/<EXP_NAME>/
├── checkpoints/
│   ├── best_eval_sort_accuracy.pt
│   ├── last.pt
│   └── ... 중간 체크포인트
├── effective_config.json
├── eval_history.jsonl
├── train_summary.json
└── ... TensorBoard 기록
```

`best_eval_sort_accuracy.pt`는 중간 분류 정확도가 가장 좋았던 모델입니다. 동점이면 먼저 나온 모델을 유지합니다.
`last.pt`는 정상 종료 시점의 모델이며 가장 좋은 모델이라는 보장은 없습니다.
원본의 0부터 시작하는 반복 번호를 유지했으므로 중간 파일명과 실제 갱신 수가 1 차이 날 수 있습니다.
정확한 값은 `completed_updates`를 확인하세요.

### 저장한 모델을 다시 불러 평가

위 학습이 성공한 뒤 **같은 EXP_NAME**으로 실행합니다.

```bash
WAREHOUSE_GPU=0 scripts/run_v100.sh eval.py \
  difficulty=easy obs_mode=state num_envs=2 seed=123 \
  render_backend=none capture_video=false \
  policy=warehouse_sort.il_policy:load_dp \
  checkpoint="il/baselines/diffusion_policy/runs/$EXP_NAME/checkpoints/last.pt" \
  eval_config=conf/eval/smoke.yaml \
  hydra.run.dir="runs/eval-$EXP_NAME-last"

cat "runs/eval-$EXP_NAME-last/metrics.json"
```

이 예제는 시드 5000, 5001의 **2개 에피소드**로 동작을 확인합니다. 정확도를 안정적으로 비교하기에는 적습니다.
최고 모델도 확인하려면 `last.pt`를 `best_eval_sort_accuracy.pt`로 바꾸고 출력 폴더 끝도 `-best`로 바꾸세요.
평가 출력 폴더도 실험마다 구분해야 이전 `metrics.json`을 보존할 수 있습니다.

## 6. 무엇을 바꾸며 실습할까

처음에는 파일을 계속 편집하는 대신 위 명령의 값을 바꾸면 실험 조건을 추적하기 쉽습니다.
Hydra 설정에서 이미 있는 항목은 `flags.foo=값`, YAML에 없는 항목을 추가할 때는 `+flags.foo=값`을 사용합니다.

| 목적 | 명령에서 바꿀 값 | 의미/주의점 |
|---|---|---|
| 데이터 양 비교 | `+flags.num_demos=20`, `100`, `200` | 현재 파일에서 사용할 시범 수. 최대 200 |
| 더 오래 학습 | `flags.total_iters=5000` | 가중치 갱신 횟수 |
| 배치 크기 비교 | `flags.batch_size=64`, `128`, `256` | 메모리와 학습에 모두 영향 |
| 학습률 비교 | `+flags.lr=0.0001` 또는 `0.00005` | 가중치를 얼마나 크게 바꿀지 |
| 반복 실험 | `+flags.seed=2` | 초기화·샘플링 난수 시드. 기본 1 |
| 중간 평가 주기 | `flags.eval_freq=1000` | 자주 평가하면 학습 전체 시간 증가 |
| 중간 평가 분량 | `flags.num_eval_episodes=16` | 점수의 변동성을 줄일 때. 환경 수의 배수 사용 |
| 평가 병렬성 | `flags.num_eval_envs=4` | GPU 수가 아닌 시뮬레이터 수 |
| 정기 저장 주기 | `flags.save_freq=1000` | 저장 공간 사용량에 영향 |
| 실험 구분 | `flags.exp_name=새이름` | 매번 새 이름 사용 |

권장 순서:

1. 20개/1,000회로 학습 → 저장 → 평가의 전체 흐름을 직접 확인합니다.
2. 반복 수와 나머지 조건을 고정하고 데이터 수만 20/100/200으로 비교합니다.
3. 전체 200개에서 반복 수나 학습률을 **한 번에 하나씩** 바꿉니다.
4. 같은 평가 조건과 여러 학습 시드에서 비교합니다.
5. 이후 추론 설정, 신경망 구조, 환경 변경 순서로 확장합니다.

### Horizon과 모델 구조는 두 번째 단계

- `obs_horizon=2`: 관측 2시점을 조건으로 사용.
- `pred_horizon=16`: 한 번에 예측하는 행동 구간 길이.
- `act_horizon=8`: 학습기 내부 평가에서 예측 행동 중 연속 실행하는 길이.
- `unet_dims=[64,128,256]`: 신경망 각 단계의 채널 수.

이 값들은 단순히 반복 수를 바꾸는 것보다 영향 범위가 큽니다.
`warehouse_sort/il_policy.py`의 `load_dp()`도 학습한 모델에 맞는 horizon과 네트워크 설정으로 불러와야 합니다.
체크포인트에 args가 들어 있어도 현재 로더가 이를 자동으로 전부 적용하지는 않습니다.
구조를 바꾸면 별도 로더 함수를 만들어 `policy=모듈:함수`로 지정하는 방식이 좋습니다.
현재 state 로더는 최근 2시점을 중심으로 관측 이력을 구성하므로 `obs_horizon>2` 실험에는 실제 이력 버퍼 구현도 검토해야 합니다.

특히 **현재 학습기 내부 평가와 `eval.py`의 추론 방식이 다릅니다.**
내부 평가는 100회 노이즈 제거 후 행동을 8개씩 실행하고, 독립 평가 로더는 기본 16회 노이즈 제거 후 행동 하나를 실행하고 다시 계획합니다.
따라서 점수를 비교할 때 어떤 평가 경로를 사용했는지 반드시 함께 기록하세요.

## 7. 결과를 어떻게 읽나

| 항목 | 해석 |
|---|---|
| loss | 시범 행동에 더한 노이즈 예측 오차. 작아져도 실제 작업 성공률이 반드시 증가하지 않음 |
| sort_accuracy | 전체 택배 중 올바른 분류함에 들어간 비율 |
| all-placed / success at end | 에피소드 끝에서 모든 택배를 올바르게 놓은 비율 |
| mis-sort | 잘못된 분류함에 들어간 비율. 0이어도 택배를 아예 옮기지 못했을 수 있음 |
| elapsed / training time | 실제 경과 시간. 현재 학습 요약 시간에는 중간 평가 포함 |

기존 본학습 결과:

| 조건 | 결과 |
|---|---|
| 시범/갱신 수 | 전체 200개 / 30,000회 |
| 학습 시간 | 40분 10초 |
| 최고 내부 분류 정확도 | 46.875%, 10,001회 갱신 시점 |
| 마지막 내부 분류 정확도 | 43.75% |
| 최고 모델의 독립 20개 에피소드 평가 | 35%, 총 40개 택배 중 14개 정분류 |
| 독립 평가에서 2개 모두 정분류 | 0/20 에피소드 |

시범 생성 시드는 1000–1199, 최종 평가는 100000–100019를 사용했습니다.
easy는 배치가 고정되어 있으므로 새로운 시드의 평가를 새로운 배치 일반화 검증으로 해석하면 안 됩니다.
설정을 고를 개발용 평가 시드와 마지막 확인용 시드를 구분하세요. 최종 시드로 계속 튜닝하면 독립 시험의 의미가 약해집니다.
현재 평가에서 raw `mean_steps=100`은 미완료 표시값이므로 “100스텝에 성공”으로 해석하면 안 됩니다.

자세한 결과와 곡선: [본학습 기록](../experiments/2026-09-15-easy-full.md).

TensorBoard로 학습 기록을 볼 수도 있습니다.

```bash
.venv/bin/tensorboard \
  --logdir il/baselines/diffusion_policy/runs \
  --host 127.0.0.1 --port 6006
```

서버의 6006번 포트를 SSH 도구의 포트 전달 기능으로 연결해 브라우저에서 확인합니다.
그래프 서버를 종료하는 것은 별도 프로세스의 학습을 종료하는 동작이 아닙니다.

## 8. 기존 실행 스크립트의 용도와 제한

| 스크립트 | 현재 용도 |
|---|---|
| `scripts/train_smoke.sh` | 4개 시범/20회 실행 확인. 추가 인수를 받을 수 있으므로 새 `flags.exp_name` 지정 가능 |
| `scripts/eval_smoke.sh` | 기존 smoke 체크포인트 평가. 새 실험에는 경로와 출력 폴더 override 필요 |
| `scripts/train_easy_full.sh` | 완료한 200개/30,000회 실험의 정확한 실행 조건. 이름 고정, 기존 폴더 존재 시 중단 |
| `scripts/eval_easy_full.sh` | 기존 본학습의 최고 모델과 20개 시드 평가. 모델과 출력 폴더 고정 |
| `scripts/summarize_easy_full.py` | 기존 30,000회 실험 전용 집계. 임의 실험용 범용 집계기가 아님 |
| `scripts/fetch_easy_state.py` | Kaggle 파일 목록 확인, `--download`로 easy/state 두 파일만 다운로드 |

두 `*_easy_full.sh`는 추가 인수를 전달하는 구조가 아닙니다. 뒤에 설정을 붙여 새 실험으로 바꾸려 하지 말고 5절의 직접 명령을 사용하세요.
완료된 본학습 폴더 `warehouse_state_dp_easy_full_30k`와 모델은 그대로 보존합니다.
현재 체크포인트에는 모델/EMA 가중치와 설정은 있지만 optimizer와 RNG 상태는 없습니다. 중단 지점부터 동일한 학습을 정확히 재개하는 기능은 아직 없습니다.

## 9. 환경이나 알고리즘을 바꾸고 싶다면

- **새 난이도:** `conf/difficulty/`와 해당 난이도 시범 데이터를 함께 확인합니다. 현재 state 차원은 택배 수에 따라 달라지므로 easy 체크포인트를 그대로 medium/hard에 적용할 수 없습니다.
- **성공 판정·보상·물체 배치:** `warehouse_sort/env.py`. 이 변경은 비교하는 문제 자체를 바꾸므로 별도 실험으로 기록합니다.
- **학습 손실·optimizer·데이터 샘플링:** 실제 baseline `train.py`.
- **모델 크기·구조:** baseline Args/설정과 `conditional_unet1d.py`, 대응하는 로더.
- **추론 속도·행동 실행 방식:** `warehouse_sort/il_policy.py`. 학습기 내부 평가와 동일하게 만들려면 양쪽 평가 경로를 함께 점검합니다.
- **영상:** Vulkan 과제를 먼저 해결해야 합니다. state 실습에서는 `capture_video=false`, `render_backend=none` 유지.

## 10. 실험 기록과 Git

실험마다 `experiments/<날짜>-<실험명>.md`를 만들고 다음을 기록하세요.

```text
실험 목적 / 변경한 변수
코드 커밋 / 실행 명령 / 실제 적용 설정
데이터 시범 수 / 학습 시드 / 평가 환경 시드
학습 시간 / 중간 분류 정확도 / 최종 분류 정확도와 전체 성공률
평가 경로와 추론 설정
최고·마지막 모델의 로컬 경로
관찰한 문제와 다음 실험
```

Git에는 코드, 설정, 간결한 결과를 올립니다. `.venv`, 시범 데이터, 모델, 상세 로그, 인증 파일은 기존 `.gitignore` 제외 대상입니다.
공유할 파일만 명시해서 추가하고 diff를 확인합니다.

```bash
git status --short
# 아래 파일명은 실제 작성한 실험 기록 경로로 바꿉니다.
git add experiments/2026-09-15-easy-practice-001.md
git diff --cached
git commit -m "Document easy state practice experiment"
git push origin main
```

공식 코드 출처와 라이선스 확인 내역은 [UPSTREAM.md](UPSTREAM.md), 설치 재현은 [SETUP_V100.md](SETUP_V100.md)를 참고하세요.
