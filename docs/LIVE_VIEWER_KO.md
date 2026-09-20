# 실시간 브라우저 관람 — VS Code Remote Tunnels

## 현재 구성

서버 PhysX 시뮬레이터에서 기존 최고 모델을 실행하고, 실제 로봇 링크·상자·분류함의 위치와 회전을 브라우저로 전송합니다.
PC의 WebGL로 Panda 원본 GLB 메시와 상자·분류함을 그립니다. MP4 재생이 아니라 실행 중 상태를 보여주는 화면입니다.
SAPIEN의 카메라 영상을 스트리밍하는 방식은 아니며, 재질·조명·탁자와 분류함의 표현은 별도로 구성한 관람용 장면입니다.
모델 입력은 계속 **state**이고 관람 카메라를 회전해도 모델에 영향을 주지 않습니다.

- 모델: `warehouse_state_dp_easy_full_30k/checkpoints/best_eval_sort_accuracy.pt`의 EMA
- 검증 SHA256: `131f25d665933d4ff5e452c5909b60f56cedc902d6ee45a3fda747afd2401527`
- DDPM 100회, 예측 16개 중 인덱스 1:9의 행동 8개 실행, FrameStack 관측 2개.
- 기존 학습기의 Agent / make_eval_envs 재사용. 새 학습 없음.
- GPU 0 한 대, 동시에 4개 환경(시드 100000–100003). 화면에서 관람할 환경 선택 가능.
- 최초 접속은 시범 70스텝 복원 후 일시정지 상태. 시범 재생은 45스텝, 모델은 200스텝 후 자동 일시정지. 현재 터미널 종료까지 모델은 GPU 메모리에 유지됩니다.
- 원래 시작 모드는 정렬 평가 첫 배치와 같은 시드를 사용합니다. 시범 70스텝 진단 모드는 동일 물리 상태와 69·70 관측을 네 환경에 복원하고 추론 시드 20260915를 고정합니다.
- 원래 시작 모드의 “처음부터”는 환경 시드와 관측 이력·행동 큐를 초기화하지만 정책 난수 흐름은 이어집니다. 시범 70스텝 진단 모드는 추론 시드까지 복원합니다. 따라서 매번 완전히 동일한 궤적을 보장하지 않습니다. 원래 평가 결과를 대체하는 채점 도구가 아닙니다.

## 1. 접속: 데스크톱 VS Code 원격 터널

1. `pepe-student`에 연결된 현재 VS Code 창을 사용합니다.
2. 하단 패널의 **Ports / 포트**를 엽니다. 안 보이면 명령 팔레트에서 `Ports: Focus on Ports View` 또는 포트 뷰 열기를 검색합니다.
3. **Forward a Port / 포트 전달**을 눌러 **8765**를 입력합니다.
4. 포트의 **Visibility / 표시 범위가 Private / 비공개**인지 확인합니다. Public으로 변경하지 않습니다.
5. 해당 행의 **Open in Browser / 브라우저에서 열기**를 누릅니다.
6. 로그인 화면이 뜨면 현재 원격 터널에 사용하는 계정으로 인증합니다.
7. 화면의 **시작 / 계속**을 누릅니다. 드래그로 회전, 휠로 확대, 우클릭 드래그로 시점을 이동합니다.

VS Code가 만든 주소를 사용하세요. 터널 형태에 따라 localhost 주소 또는 인증된 devtunnels 주소일 수 있습니다.
서버 IP의 `:8765`로 직접 접속하거나 공유기/방화벽 포트를 열 필요가 없습니다.
서버는 코드에서 **127.0.0.1에만 바인딩**하며 공개 주소 바인딩 옵션을 제공하지 않습니다.
VS Code의 실제 터널 접속은 사용자의 데스크톱에서 마지막으로 확인해야 합니다. 서버 로컬 브라우저 테스트는 통과했습니다.

공식 안내: [VS Code 포트 전달](https://code.visualstudio.com/docs/debugtest/port-forwarding), [Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels).

## 2. 실행과 종료

이미 서버가 실행 중이면 새로 실행할 필요 없이 포트만 전달하세요.
다음 명령으로 로컬 상태를 확인할 수 있습니다.

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
.venv/bin/python -c "import json,urllib.request; s=json.load(urllib.request.urlopen('http://127.0.0.1:8765/state')); print(s['status'], s['step'], s['playing'])"
```

새로 실행할 때:

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
WAREHOUSE_GPU=0 scripts/run_v100.sh scripts/live_viewer.py --port 8765
```

이 터미널에서 **Ctrl+C**를 누르면 서버와 시뮬레이터를 종료하고 GPU 메모리를 해제합니다.
현재처럼 별도 세션에서 실행 중인 서버를 다른 터미널에서 종료하려면:

```bash
cd '/home/student/projects/Robot Parcel Sorting Challenge'
kill -INT "$(cat runs/live-viewer.pid)"
```

브라우저 탭이나 VS Code 포트 전달만 닫으면 실행 중 시뮬레이터는 즉시 종료되지 않습니다.
화면의 일시정지 버튼은 추론/물리 진행을 멈추고, 서버 종료는 메모리까지 해제합니다.
실행 버튼 이후 화면을 닫아도 최대 200스텝에서 자동 정지하므로 무한 반복하지 않습니다.

포트가 이미 사용 중이면 기존 서버를 확인하거나 `--port 8766`으로 실행하고 그 번호를 비공개 전달하세요.
이 프로젝트의 관람 서버는 한 인스턴스만 사용하세요(PID 파일 공유).

## 3. 파일 역할

| 파일 | 역할 |
|---|---|
| `scripts/live_viewer.py` | 127.0.0.1 HTTP 서버, 기존 모델 로딩, 실제 시뮬레이션, 상태 전송, 제어 |
| `web/live-viewer/index.html` | 관람 화면, 버튼, 에피소드 선택, 지표 패널 |
| `web/live-viewer/viewer.js` | 로봇 메시 로딩, 실제 자세 적용, WebGL 렌더링, 카메라 |
| `scripts/build_live_viewer.py` | 로컬 3D 코드를 단일 파일로 번들링(고정 버전 esbuild) |
| `scripts/setup_live_viewer_assets.py` | 고정 버전 Three.js를 프로젝트 캐시에 다운로드·해시 검사 |
| `scripts/check_live_viewer_browser.py` | 개발용 실제 브라우저 동작 검사 |
| `scripts/run_v100.sh` | 프로젝트 Python과 로컬 라이브러리, GPU 선택 |

데이터 전송은 SSE 지속 연결로 관람 중인 환경 하나의 최신 자세만 보냅니다. 균형 품질은 최대 15Hz이며, 실제 새 상태 속도는 추론·물리 속도에 제한됩니다. SSE 오류/장기 지연 시 HTTP polling으로 복구하고 재연결합니다. 브라우저 렌더링은 모델 실행 및 상태 수신과 독립적으로 동작합니다.
물리 진행은 최대 20스텝/초로 제한하며 100회 노이즈 제거 중에는 새 상태가 잠시 도착하지 않을 수 있습니다.
실시간 관람이지만 1초의 물리 시간을 반드시 1초의 벽시계 시간에 처리한다는 보장은 없습니다.
상자 정분류 표시는 환경의 누적 `_placed_correct`이고, 잡기는 상자별 실제 `is_grasping`입니다.

## 4. 패키지와 설치 범위

실행 서버는 Python 표준 라이브러리와 기존 `.venv` 패키지만 사용합니다. `.venv` 패키지 구성을 바꾸지 않았습니다.
Three.js **0.170.0 (MIT)**는 `.cache/live-viewer/`에만 저장하며, 접속 시 외부 CDN을 호출하지 않습니다.
원본 로봇 메시도 설치된 ManiSkill 자산에서 읽어 허용된 GLB 파일만 제공합니다. 전체 프로젝트 파일을 웹에 노출하지 않습니다.

캐시를 삭제한 경우에만:

```bash
.venv/bin/python scripts/setup_live_viewer_assets.py
.venv/bin/python scripts/build_live_viewer.py
```

Three.js 출처: `https://registry.npmjs.org/three/-/three-0.170.0.tgz`
SHA256: `4a608a355dcaba72e0e5383cdc814303f5b6060b43c238cdf6932dceb699238d`.
라이선스는 `.cache/live-viewer/LICENSE`, 파일별 해시는 `.cache/live-viewer/manifest.json`입니다.
로봇 자산은 기존 ManiSkill 설치를 참조하며 별도로 저장소에 재배포하지 않습니다.

개발용 화면 검증은 `uv run --no-project --with playwright`의 별도 캐시 환경과 Chromium을 사용했습니다.
브라우저 시험에 필요한 공유 라이브러리만 `.cache/browser-test-libs/`에 `.deb`를 추출했습니다.
`apt-get download`/`dpkg-deb -x`만 사용했으며 시스템 패키지 설치·업데이트와 관리자 권한 사용은 없었습니다.
처음에는 libnspr4/libnss3 등 누락으로 Chromium이 실행되지 않았습니다. 캐시 라이브러리로 해결했습니다.
일부 오래된 apt 인덱스의 업데이트 버전 URL이 404여서 Ubuntu noble 기본 저장소의 명시된 버전을 다운로드했습니다.
이 서버측 시험용 브라우저는 사용자의 PC 접속에는 필요하지 않습니다.

## 5. Vulkan / 데스크톱 조사 결과 — 2026-09-17

- 호스트 이름: pepe-student, NVIDIA 드라이버 570.133.20, V100 4대.
- `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_SESSION_TYPE` 없음; `/tmp/.X11-unix`에 디스플레이 소켓 없음.
- Xorg/Xvnc/x11vnc/xrdp/weston 명령과 해당 프로세스가 발견되지 않음. 현재 계정에서 활용 가능한 기존 원격 데스크톱을 찾지 못함.
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility`.
- 표준 Vulkan ICD 디렉터리에 사용 가능한 NVIDIA ICD가 없고 SAPIEN은 호환 드라이버를 찾지 못함.
- `scripts/run_v100.sh scripts/smoke_runtime.py render` 재검증 오류: `RuntimeError: vk::createInstanceUnique: ErrorIncompatibleDriver`.
- `ss` 명령이 없어 실제 리슨 주소는 `/proc/net/tcp`로 확인했습니다.

SAPIEN 자체 카메라 렌더링을 복구하려면 관리자에게 컨테이너의 NVIDIA `graphics` capability 및 호스트와 일치하는 Vulkan/OpenGL 사용자 라이브러리·ICD 노출을 확인받아야 합니다.
직접 X11 데스크톱을 사용할 경우 `display` capability와 디스플레이 서버 구성도 검토해야 합니다.
이는 원인에 근거한 조사 요청이지, 호스트 드라이버 업그레이드가 필요하다고 확정한 것은 아닙니다.
현재 브라우저 관람 방식에는 이러한 관리자 작업이 필요하지 않으며 관련 설정을 변경하지 않았습니다.

공식 근거: [NVIDIA Container Toolkit의 driver capabilities](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html).

## 검증 기록

[2026-09-17 실행 및 브라우저 검증](../experiments/2026-09-17-live-viewer.md)

## 페이지는 열리지만 화면이 비어 있을 때

페이지를 `Ctrl+Shift+R`로 새로고침하세요. 서버 상태와 제어 버튼은 이제 3D 코드 로딩과 별도로 동작합니다.
3D 코드는 현재 HTML에 번들로 포함됩니다. WebGL/로봇 메시 초기화에 실패하면 오류 문구와 함께 Canvas 호환 화면으로 전환합니다.
호환 화면은 실제 링크·상자 좌표를 고정 시점으로 투영한 단순 도형이며 Panda 원본 메시 화면과 다릅니다. 모델 입력과 물리 실행은 동일합니다.
표시된 `WebGL 초기화`, `코드 로딩`, `로봇 메시 로딩`, `서버 연결` 오류 문구로 실패 단계를 구분할 수 있습니다.
사용자 스크린샷만으로 실제 PC의 정확한 실패 원인은 확정하지 않았습니다.
정상 WebGL, WebGL 비활성화, 모듈 요청 차단 세 경우에서 상태·버튼·화면 표시를 브라우저로 검증했습니다.

## 터널 다운로드 지연 개선

사용자 화면에서 3D 코드 다운로드 20초 초과와 상태 요청 10초 초과가 확인됐습니다. 로컬 응답은 수 ms였으나 실제 사용자 PC의 지연 발생 지점까지 확정한 것은 아닙니다.
현재는 여러 JS 모듈(약 1.5MB)을 별도로 요청하지 않고 고정 esbuild 0.25.0으로 번들링해 HTML에 포함합니다.
HTTP/1.1 keep-alive와 gzip을 사용하며 초기 HTML+코드는 약 154KB, 초기 상태 응답은 약 1.9KB입니다.
로봇 메시 11개를 순차 다운로드해 상태/제어 요청의 연결 슬롯을 남겨 두고 브라우저에 메시를 캐시합니다.
상태 요청 타임아웃은 10초, 제어 요청은 30초이며, 그림에 마지막 상태가 남아 있어도 연결 오류가 표시되면 최신 상태가 아닐 수 있습니다.
모델이나 시뮬레이터 설정은 바꾸지 않았고 바인딩은 127.0.0.1로 유지했습니다.
`viewer.js`를 수정한 경우 `scripts/build_live_viewer.py`를 다시 실행해야 반영됩니다.

## 시범 70스텝부터 시범과 모델 비교

실행 방식 메뉴에서 `시범 70 → 남은 시범 행동` 또는 `시범 70 → 기존 모델`을 선택하세요. 선택 시 자동으로 해당 시작점에 복원하고 일시정지합니다.
진단 모드는 장면 시드가 다른 네 사례가 아니라 하나의 동일 상태 복제 4개입니다. [복원 검증 및 비교 결과](../experiments/2026-09-17-demo70-comparison.md)를 참고하세요.

## 화면 끊김 조절과 성능 표시 — 2026-09-18

접속 중인 페이지를 **Ctrl+Shift+R**로 새로고침하세요. 화면 품질을 선택할 수 있습니다.

| 품질 | CSS 폭 대비 렌더 배율 / 최대 폭 | 상태 전송 상한 | 표시 좌표 소수 자릿수 |
|---|---|---|---|
| 가볍게 | 0.65 / 960px | 8Hz | 3 |
| 균형(기본) | 1 / 1280px | 15Hz | 4 |
| 선명하게 | 1.5 / 1920px | 20Hz | 5 |

실제 렌더 폭은 창 크기에 따라 상한보다 작을 수 있습니다. JPEG/영상 압축 품질이 아니라 WebGL 해상도와 좌표 전송량 설정입니다. 좌표 반올림은 관람 화면에만 적용합니다. 상태 입력, 모델, 물리 시뮬레이션은 바뀌지 않습니다.

- **움직임 보간**: 수신한 두 자세 사이를 최대 80ms 동안 연결해 표시합니다. 물리적으로 계산한 중간 상태는 아니므로 정확한 자세를 확인할 때 끄세요. 새로운 행동을 예측하거나 추론 중 움직임을 만들어내지는 않습니다.
- 수신 대기열은 최신 상태 하나로 덮어씁니다. 서버도 과거 프레임을 보관해 재생하지 않습니다. 느린 연결은 쓰기 제한시간으로 끊고, 프록시가 지연시킨 스트림은 클라이언트가 감지해 최신 상태 요청으로 복구합니다. 운영체제·프록시 내부 버퍼까지 없애는 것은 아닙니다.
- **표시 FPS**는 이 PC 브라우저의 실제 그리기 호출 빈도입니다. 모니터의 최종 스캔아웃 FPS를 측정하는 것은 아닙니다. **새 상태 Hz**는 새로운 시뮬레이터 상태 수신 빈도이며 추론 중에는 감소합니다.
- RTT는 상태 요청 왕복시간입니다. **상태 나이(추정)**는 화면에 표시하는 자세가 생성된 이후 경과시간으로, 네트워크 지연·보간·추론 정지를 모두 포함합니다. 시계 차이는 요청 왕복 중간값으로 보정하므로 비대칭 통신에서는 오차가 있습니다.
- 추론/묶음과 물리/스텝은 서버 계측 평균입니다. `/profile`에서 상세 수치를 볼 수 있습니다. 시범 재생 모드에는 모델 추론이 없습니다.
- WebGL 실패 시 단순 Canvas 호환 화면으로 복구하며 이 모드에서는 WebGL FPS를 표시하지 않습니다.

[측정 조건·변경 전후 결과](../experiments/2026-09-18-viewer-performance.md). 측정 스크립트는 `scripts/benchmark_live_viewer.py`, 품질·스트림·호환 화면 검증은 `scripts/check_live_viewer_stream.py`입니다.

현재 DDPM 100회와 행동 묶음 8개를 유지하므로 약 0.9초의 추론 정지는 남습니다. 추론 횟수 감소 또는 행동 묶음 길이 변경은 정책 행동과 성공률을 바꿀 수 있는 별도 실험이며 적용하지 않았습니다.

## 첫 상자 분류 후 준비 이동 실험

별도 `prepare` 모드는 한 환경에서 첫 정분류 후 정상 행동 명령으로 집게 열기·상승·준비 위치 이동을 수행하고 실제 관측으로 모델을 재개합니다. 기존 모드는 유지됩니다. [실행 및 코드 안내](READY_INTERVENTION_KO.md), [단일 에피소드 기능 확인](../experiments/2026-09-20-ready-intervention.md).
