# Related Work & Design Rationale

> 이 문서는 심사 Q&A 방어용 근거 자료다.  
> **인용 원칙**: 사실이 확인된 것만 기재하며, 불확실한 세부사항은 명시한다.

---

## 1. 문제의식

기존 AI 에이전트 관측 도구(LangSmith, Langfuse 등)는 실행된 경로(**trace**)만
추적한다. 에이전트가 어떤 대안을 고려했고 왜 버렸는지, 그리고 그 선택의
기회비용이 얼마인지는 남지 않는다.

Nexus는 관측의 원자 단위를 재정의한다:

```
trace  →  decision = (선택 + 버려진 대안 + 기회비용 + replay payload)
```

이 단위를 capture → store → replay → diff 하는 것이 Nexus의 핵심 파이프라인이다.

---

## 2. 관련 연구

### 2.1 Causal Agent Replay (CAR)

> Shah, J. et al. "Causal Agent Replay."  
> arXiv:2606.08275 (2026), Carnegie Mellon University.

**핵심 주장**

CAR은 LLM에게 에이전트 전사(transcript)를 보여주고 귀책(attribution)을 묻는
접근이 근본적으로 신뢰할 수 없음을 실험적으로 보인다.  
Who&When 벤치마크에서 최고 스텝 단위 귀책 정확도가 약 **14%** 에 그쳤으며,
논문은 그 이유를 상관관계 기반 추론의 한계로 설명한다.

CAR이 제안하는 원리적 대안은 **인과적 개입(do-operation)**: 특정 스텝에 개입해
에이전트를 재실행하고, 결과 변화를 직접 측정한다.

**Nexus와의 관계**

CAR은 "설명이 아니라 재실행"이 옳다는 주장을 학술적으로 뒷받침하며,
Nexus의 replay-then-diff 설계의 이론적 근거가 된다.

**차별점**

| 항목 | CAR | Nexus |
|---|---|---|
| 검증 환경 | 합성 구조적 인과모델(synthetic SCM), 도구는 mock | 실제 배포 환경 상정, side-effect 도구 포함 |
| side-effect 처리 | 명시적으로 범위 밖 — mocked 도구만 사용 | record-and-replay 샌드박스: `SIMULATED` 마킹으로 안전하게 재생 |
| 목적 | 사후 디버깅·귀책 | 디버깅 + **기회비용 달러 정량화** + 개발자 계측 SDK |
| 형태 | 연구 논문 | 배포 가능한 오픈소스 SDK (`pip install nexus-sdk`) |

---

### 2.2 LLM 자기설명 및 counterfactual의 충실성(faithfulness)

**알려진 문제**: LLM이 생성한 자기설명이나 counterfactual은 그럴듯하지만
(plausible), 모델이 실제로 사용한 내부 로직을 반영하지 않을 수 있다.

대표 연구:

> Turpin, M., Michael, J., Perez, E., & Bowman, S. R.  
> "Language Models Don't Always Say What They Think: Unfaithful Explanations in  
> Chain-of-Thought Prompting."  
> *NeurIPS 2023.* arXiv:2305.04388.

이 논문은 CoT 설명이 모델의 실제 추론을 반영하지 않는 사례를 체계적으로 보이며,
특히 편향된 프롬프트(biasing features)가 있을 때 CoT가 실제 영향 요인을 숨길 수
있음을 실험적으로 입증한다.

**설계 함의**

Nexus는 `cost_delta` 와 대안 비교 값을 **LLM에게 묻지 않는다**.  
결정 시점에 캡처된 `chosen.cost` 와 `alternatives[i].cost` 를 DB에서 읽어
순수 산술 연산(`chosen.cost - alt.cost`)으로만 계산한다.  
이는 LLM 충실성 문제를 설계 수준에서 원천 차단한다.

---

### 2.3 Record-and-Replay의 계보

결정론적 record-and-replay(기록 후 재생)는 수십 년간 검증된 디버깅 기법이다.  
대표적으로 Mozilla의 **`rr`**(https://rr-project.org)는 Linux 프로세스 실행을
결정론적으로 기록하고, 역방향 디버깅까지 지원한다.

Nexus의 replay 샌드박스는 이 계보를 **LLM 에이전트 의사결정 단위**에 적용한 것이다.  
차이는 단위(syscall/instruction → agent decision)와 목적(버그 재현 → 대안 탐색)이며,
핵심 원리인 "실행 당시 입출력을 캡처해두고 나중에 재생한다"는 동일하다.

---

## 3. 설계 원칙 (코드와 일치)

| 원칙 | 구현 위치 | 세부 |
|---|---|---|
| cost_delta는 캡처값 전용 | `replay.py` | `float(chosen.cost) - float(alt.cost)`, LLM 호출 없음 |
| side_effects_executed 항상 0 | `replay.py:replay_decision()` | 엔진이 직접 카운트해 반환, 우회 불가 |
| 조회 도구 → REPLAYED | `replay.py:_is_side_effect()` | 기록된 outputs 그대로 반환 |
| side-effect 도구 → SIMULATED | `replay.py:_is_side_effect()` | 실제 실행 없이 마킹만 |
| 에이전트 불중단 | `tracer.py:_ship()` | 전송 실패 시 WARNING 출력, 예외 전파 없음 |

---

## 4. 한계 및 향후 연구 방향

### 현재 한계

**Side-effect 판별의 완전성**  
현재는 `replay_payload.tools[].type: "side_effect"` 명시적 태깅을 1차로 확인하고,
누락 시 도구 이름 키워드(`execute`, `refund`, `send` 등)로 분류한다.  
이름이 모호한 도구나 태깅되지 않은 도구는 보수적으로 `query`(안전)로 처리하나,
완전한 정확성을 보장하지는 않는다.

**복수 결정의 인과 연쇄**  
현재 replay는 단일 결정 단위로 독립 수행된다.  
에이전트가 연속된 결정을 내리고 앞 결정의 결과가 뒤 결정의 입력이 되는 경우,
전체 경로 replay는 아직 지원하지 않는다.

**집계의 해석**  
`/aggregate`의 `total_opportunity_cost`는 각 결정에서 달성 가능한 최대 절감액의
단순 합산이다. 결정 간 상호의존성(예: 한 결정의 대안을 택하면 다음 결정의 선택지가
달라지는 경우)은 반영되지 않는다.

### 향후 방향

- 복수 결정의 **경로 수준 counterfactual**(전체 run replay)
- 도구 타입 **자동 분류 모델** 또는 레지스트리 기반 관리
- CAR의 do-operation 개입 방식을 Nexus SDK와 통합해 학술 실험 재현성 지원

---

## 참고문헌

1. Shah, J. et al. "Causal Agent Replay." arXiv:2606.08275, 2026.  
   https://arxiv.org/abs/2606.08275

2. Turpin, M., Michael, J., Perez, E., & Bowman, S. R.  
   "Language Models Don't Always Say What They Think: Unfaithful Explanations in  
   Chain-of-Thought Prompting." *NeurIPS 2023.* arXiv:2305.04388.  
   https://arxiv.org/abs/2305.04388

3. Mozilla `rr` — deterministic record-and-replay debugger.  
   https://rr-project.org  
   Source: https://github.com/mozilla/rr
