# 연동 현황 (2026-10-16 점검)

| 연동 | 상태 | 비고 |
|---|---|---|
| 주소 정규화 `maps_geocode` | 동작 확인 | |
| 건축물대장 `bld_register` | 동작 확인 | 주소로 조회 시 인근 필지로 대체되나 결과는 정확 |
| K-apt ① 단지목록 `AptListService4` | **동작 확인** | 일산동구(41285) 115개 단지 조회. 우리 단지 = `A10027517` 일산와이시티(백석동). 오퍼레이션 `getSigunguAptList4`(파라미터 sigunguCode) |
| K-apt ② 기본정보 `AptBasisInfoServiceV5` | **권한 OK, 결과 0건** | `getAphusBassInfoV5/getAphusDtlInfoV5` kaptCode 조회 시 0건. 오퍼레이션명·파라미터 미확인 또는 gov_raw가 응답 형태를 못 읽는 것으로 추정 |
| K-apt ③ 공용관리비 `AptCmnuseManageCostServiceV3` | **권한 OK, 결과 0건** | 오퍼레이션 17종(getHsmpGuardCostInfoV3, getHsmpCleaningCostInfoV3, getHsmpElevatorMntncCostInfoV3, getHsmpRepairsCostInfoV3, getHsmpConsignManageFeeInfoV3 등). 파라미터 kaptCode+searchDate(YYYYMM) 추정. 빈 파라미터도 0건이라 원인 구분 불가(원본 응답을 볼 수 없음) |
| 법령 본문 (law.go.kr) | **Firecrawl로 동작 확인** | 네트워크 허용 후에도 직접 접속(curl)은 연결 끊김(해외 IP 차단 추정). `firecrawl_scrape`로 공동주택관리법 본문 수신 확인(2026-10-16, 캐시본) |
| 국가법령정보 Open API (인증키) | 미설정 | 현재는 Firecrawl로 대체 가능. 키 발급은 선택 |
| k-apt.go.kr 직접 접속 | **연결 끊김** | 첫 접속은 200이나 이후 재접속 실패. Firecrawl로 우회 시험 필요 |
| apis.data.go.kr | 접속됨 | 서비스 경로/활용신청 문제는 위 K-apt 행 참고 |
| 민원 여론 `search_cafearticle/blog/news` | 미시험 | 네이버 API |
| Gmail/Calendar/Drive/Notion | 연결됨, 미시험 | 일정·공고 알림용 |

## 사용자가 해야 할 일
1. 환경 네트워크 설정(세션 제목줄의 환경 메뉴 → Edit)에서 아래 호스트 허용: `www.law.go.kr`, `open.law.go.kr`, `www.k-apt.go.kr`, `apis.data.go.kr`
2. data.go.kr에서 "공동주택 단지 목록/기본정보/관리비정보" 계열 API를 **활용신청** (이 MCP의 serviceKey와 같은 계정). 승인된 서비스명을 알려 주면 경로를 맞춘다.
3. 법령 API 사용 시 law.go.kr OPEN API 신청으로 OC 인증키 발급 (환경 시크릿으로 등록, 대화에 붙여넣지 말 것)
