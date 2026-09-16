# 담양군 빈집 입지 분석 및 용도 추천

전라남도 담양군의 빈집 데이터를 분석해, 주변 입지(학교·상권·관광명소 등)를 기반으로 각 빈집에 적합한 용도(주거 / 관광·숙박)를 추천하는 웹 서비스입니다.

조선대학교 오픈소스 SW 프로젝트 과목의 한 학기 프로젝트로 진행하고 있습니다.

## 무엇을 하는 서비스인가

- 담양군 공공데이터의 빈집 405건을 지도 위에 표시합니다.
- 각 빈집이 위치한 읍면의 주변 시설(학교, 편의점, 마트, 관광명소, 공원, 카페)을 분석해, 주거에 적합한지 관광·숙박(게스트하우스/카페)에 적합한지 규칙 기반으로 추천합니다.
- 지도에서 용도별로 필터링해서 볼 수 있습니다.

## 데모 화면

지도 위에 빈집 위치가 색상별(주거=파랑, 관광·숙박=주황)로 표시되고, 마커를 클릭하면 주소와 추천 용도를 확인할 수 있습니다.

## 기술 스택

| 영역 | 사용 기술 |
|---|---|
| 프론트엔드 | React (Vite), 카카오맵 JavaScript SDK |
| 백엔드 | FastAPI (Python) |
| 데이터 처리 | pandas, 카카오 로컬 API (지오코딩·키워드 검색) |
| 데이터 저장 | CSV |

## 프로젝트 구조

```
damyang-vacant-house/
├── backend/                # FastAPI 서버
│   ├── main.py
│   └── damyang_final.csv   # 최종 데이터 (좌표 + 용도 추천 포함)
├── data-pipeline/          # 원본 데이터 → 최종 데이터 가공 스크립트
│   ├── damyang_raw.csv         # 공공데이터포털 원본 (담양군 빈집정보 현황)
│   ├── geocode_damyang.py      # 주소 → 좌표 변환 (지오코딩)
│   ├── damyang_geocoded.csv    # 좌표가 붙은 중간 결과물
│   ├── geocode_facilities.py   # 읍면별 주변 시설 조회 + 용도 점수 계산
│   ├── eupmyeon_centers.csv    # 읍면별 대표 좌표
│   ├── eupmyeon_facilities.csv # 읍면별 시설 개수 + 용도 추천 결과
│   └── merge_final.py          # 빈집 데이터 + 읍면 추천 결과 병합
└── frontend/                # React 프론트엔드
    ├── index.html
    └── src/
        ├── App.jsx
        └── App.css
```

## 데이터 파이프라인

1. **원본 데이터 수집**: 공공데이터포털에서 담양군 빈집정보 현황(리 단위 주소, 405건)을 받습니다.
2. **지오코딩**: 카카오 로컬 API로 리 단위 주소를 위도·경도 좌표로 변환합니다. (`geocode_damyang.py`)
3. **주변 시설 분석**: 읍면 12곳의 대표 좌표를 기준으로, 반경 3km 이내 학교·마트·편의점·관광명소·공원·카페 개수를 조회합니다. (`geocode_facilities.py`)
4. **용도 점수화**: 학교·마트·편의점 개수로 주거 적합 점수를, 관광명소·공원·카페 밀도로 관광·숙박 적합 점수를 계산해 더 높은 쪽을 추천 용도로 결정합니다.
5. **최종 병합**: 빈집 405건 각각에 소속 읍면의 추천 용도를 매칭합니다. (`merge_final.py`)

## 실행 방법

### 사전 준비

- Python 3.x, Node.js가 설치되어 있어야 합니다.
- [카카오 개발자센터](https://developers.kakao.com)에서 애플리케이션을 만들고 REST API 키(데이터 파이프라인용)와 JavaScript 키(지도 표시용)를 발급받아야 합니다.

### 1. 백엔드 실행

```bash
cd backend
pip install fastapi uvicorn pandas
uvicorn main:app --reload
```

서버가 켜지면 `http://127.0.0.1:8000/docs`에서 API 문서를 확인할 수 있습니다.

### 2. 프론트엔드 실행

`frontend/index.html`의 카카오맵 SDK appkey를 본인의 JavaScript 키로 설정한 뒤:

```bash
cd frontend
npm install
npm run dev
```

터미널에 표시되는 주소(기본 `http://localhost:5173`)로 접속합니다. 백엔드 서버가 함께 켜져 있어야 합니다.

### 3. 데이터 파이프라인 재실행 (선택)

원본 데이터부터 다시 처리하고 싶다면 `data-pipeline` 폴더의 스크립트를 순서대로 실행합니다. 각 스크립트 상단의 `KAKAO_API_KEY`에 본인의 REST API 키를 입력해야 합니다.

```bash
cd data-pipeline
pip install requests pandas
python geocode_damyang.py       # 1. 좌표 부착
python geocode_facilities.py    # 2. 주변 시설 + 용도 점수화
python merge_final.py           # 3. 최종 데이터 병합
```

## 현재 범위와 한계

- 개인정보 보호를 위해 원본 데이터의 위치 정보가 리(里) 단위까지만 공개되어 있어, 용도 추천도 개별 필지가 아닌 읍면 단위로 계산됩니다.
- 용도 추천은 학교·상권·관광명소 개수를 단순 가중합한 규칙 기반 점수이며, 정교한 가중치 튜닝이나 머신러닝 기반 예측은 적용하지 않았습니다.
- 리모델링 비용 추정 등 추가 기능은 향후 계획입니다.

## 앞으로 할 일

- [ ] 용도 추천 점수 규칙 개선
- [ ] 지도 마커 클러스터링
- [ ] 개별 빈집 상세 정보 표시
- [ ] 리모델링 비용 등급 기능
- [ ] 배포 (백엔드/프론트엔드 호스팅)
